use crate::command::Command;
use crate::event::{Event, SubmissionMetadata};
use crate::snapshot;
use crate::world::World;
use sha2::{Digest, Sha256};
use std::fs::{self, File, OpenOptions};
use std::io::{BufRead, BufReader, Write};
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};

pub const MAX_RETAINED_CHECKPOINTS: usize = 120;

pub struct CheckpointReplay {
    pub world: World,
    pub checkpoint_path: PathBuf,
    pub replayed_events: usize,
}

#[derive(Debug, Clone)]
pub struct StorePaths {
    pub state_dir: PathBuf,
    pub seed_path: PathBuf,
    pub world_path: PathBuf,
    pub events_path: PathBuf,
    pub snapshots_dir: PathBuf,
    pub checkpoints_dir: PathBuf,
    pub migration_marker_path: PathBuf,
    io_lock: Arc<Mutex<()>>,
}

impl StorePaths {
    pub fn new(state_dir: impl Into<PathBuf>, seed_path: impl Into<PathBuf>) -> Self {
        let state_dir = state_dir.into();
        Self {
            world_path: state_dir.join("world.json"),
            events_path: state_dir.join("events.jsonl"),
            snapshots_dir: state_dir.join("snapshots"),
            checkpoints_dir: state_dir.join("checkpoints"),
            migration_marker_path: state_dir.join("vessel-events-v2.migration.json"),
            io_lock: Arc::new(Mutex::new(())),
            state_dir,
            seed_path: seed_path.into(),
        }
    }
}

pub fn ensure_dirs(paths: &StorePaths) -> Result<(), String> {
    fs::create_dir_all(&paths.state_dir).map_err(|err| err.to_string())?;
    fs::create_dir_all(&paths.snapshots_dir).map_err(|err| err.to_string())?;
    fs::create_dir_all(&paths.checkpoints_dir).map_err(|err| err.to_string())?;
    Ok(())
}

pub fn load_seed(paths: &StorePaths) -> Result<World, String> {
    load_world_from(&paths.seed_path)
}

pub fn load_world(paths: &StorePaths) -> Result<World, String> {
    load_world_from(&paths.world_path)
}

pub fn load_world_from(path: &Path) -> Result<World, String> {
    let raw = fs::read_to_string(path)
        .map_err(|err| format!("failed to read {}: {err}", path.display()))?;
    let mut world: World = serde_json::from_str(&raw)
        .map_err(|err| format!("failed to parse {}: {err}", path.display()))?;
    world.normalize();
    Ok(world)
}

pub fn save_world(paths: &StorePaths, world: &World) -> Result<(), String> {
    ensure_dirs(paths)?;
    write_json(&paths.world_path, world)
}

pub fn save_checkpoint(paths: &StorePaths, world: &World) -> Result<PathBuf, String> {
    ensure_dirs(paths)?;
    let path = paths
        .checkpoints_dir
        .join(format!("checkpoint-tick-{:010}.json", world.clock.tick));
    write_json(&path, world)?;
    prune_checkpoints(paths, MAX_RETAINED_CHECKPOINTS)?;
    Ok(path)
}

pub fn prune_checkpoints(paths: &StorePaths, retain: usize) -> Result<(), String> {
    let mut checkpoints = fs::read_dir(&paths.checkpoints_dir)
        .map_err(|err| err.to_string())?
        .filter_map(Result::ok)
        .map(|entry| entry.path())
        .filter(|path| {
            path.extension()
                .is_some_and(|extension| extension == "json")
        })
        .collect::<Vec<_>>();
    checkpoints.sort_by(|left, right| right.file_name().cmp(&left.file_name()));

    for path in checkpoints.into_iter().skip(retain) {
        // Keep the genesis checkpoint as a human-auditable recovery anchor.
        if path
            .file_name()
            .is_some_and(|name| name == "checkpoint-tick-0000000000.json")
        {
            continue;
        }
        fs::remove_file(&path)
            .map_err(|err| format!("failed to remove {}: {err}", path.display()))?;
    }
    Ok(())
}

pub fn write_snapshot(
    paths: &StorePaths,
    world: &World,
    output: Option<&Path>,
) -> Result<PathBuf, String> {
    ensure_dirs(paths)?;
    let path = output
        .map(Path::to_path_buf)
        .unwrap_or_else(|| paths.snapshots_dir.join("snapshot.json"));
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|err| err.to_string())?;
    }
    let json = snapshot::snapshot_json(world).map_err(|err| err.to_string())?;
    fs::write(&path, json).map_err(|err| format!("failed to write {}: {err}", path.display()))?;
    Ok(path)
}

pub fn append_event(paths: &StorePaths, event: &Event) -> Result<(), String> {
    let _guard = paths
        .io_lock
        .lock()
        .map_err(|_| "event log lock poisoned".to_string())?;
    append_event_unlocked(paths, event)
}

fn append_event_unlocked(paths: &StorePaths, event: &Event) -> Result<(), String> {
    ensure_dirs(paths)?;
    let mut file = OpenOptions::new()
        .create(true)
        .append(true)
        .open(&paths.events_path)
        .map_err(|err| format!("failed to open {}: {err}", paths.events_path.display()))?;
    let json = serde_json::to_string(event).map_err(|err| err.to_string())?;
    writeln!(file, "{json}").map_err(|err| format!("failed to append event: {err}"))?;
    file.sync_data()
        .map_err(|err| format!("failed to durably sync appended event: {err}"))
}

#[derive(Debug, Clone, PartialEq)]
pub struct CommittedApply {
    pub event: Event,
    pub world_saved: bool,
    pub degraded_cause: Option<String>,
    pub duplicate: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SubmissionContext {
    pub idempotency_key: String,
    pub principal_id: String,
    pub principal_scope: String,
}

impl SubmissionContext {
    pub fn validate(&self) -> Result<(), String> {
        let key = self.idempotency_key.as_bytes();
        if key.is_empty()
            || key.len() > 64
            || !key
                .iter()
                .all(|byte| byte.is_ascii_alphanumeric() || b"._:-".contains(byte))
        {
            return Err(
                "idempotency key must be 1-64 ASCII letters, digits, '.', '_', ':', or '-'"
                    .to_string(),
            );
        }
        if self.principal_id.is_empty()
            || self.principal_id.len() > 128
            || self.principal_scope.is_empty()
            || self.principal_scope.len() > 128
        {
            return Err(
                "submission principal identity and scope must be non-empty and at most 128 bytes"
                    .to_string(),
            );
        }
        Ok(())
    }
}

fn command_digest(command: &Command) -> Result<String, String> {
    Ok(format!(
        "{:x}",
        Sha256::digest(serde_json::to_vec(command).map_err(|error| error.to_string())?)
    ))
}

fn match_submission<'a>(
    events: &'a [Event],
    command: &Command,
    submission: &SubmissionContext,
) -> Result<Option<&'a Event>, String> {
    submission.validate()?;
    let digest = command_digest(command)?;
    let Some(event) = events.iter().find(|event| {
        event
            .submission
            .as_ref()
            .is_some_and(|metadata| metadata.idempotency_key == submission.idempotency_key)
    }) else {
        return Ok(None);
    };
    let metadata = event.submission.as_ref().expect("matched submission");
    if metadata.principal_id != submission.principal_id
        || metadata.principal_scope != submission.principal_scope
    {
        return Err(
            "idempotency key is already owned by a different principal or scope".to_string(),
        );
    }
    if metadata.command_digest != digest {
        return Err("idempotency key collision with a different command".to_string());
    }
    Ok(Some(event))
}

pub fn resolve_duplicate_submission(
    paths: &StorePaths,
    command: &Command,
    submission: &SubmissionContext,
) -> Result<Option<Event>, String> {
    let guard = paths
        .io_lock
        .lock()
        .map_err(|_| "event log lock poisoned".to_string())?;
    let events = read_events_unlocked(paths)?;
    let result = match_submission(&events, command, submission)?.cloned();
    drop(guard);
    Ok(result)
}

/// Apply against a clone and publish the mutation only after its authoritative
/// command envelope has been appended. An append failure therefore leaves the
/// caller's readable World byte-for-byte unchanged.
pub fn apply_authoritative(
    paths: &StorePaths,
    world: &mut World,
    command: Command,
    submission: SubmissionContext,
) -> Result<CommittedApply, String> {
    submission.validate()?;
    let digest = command_digest(&command)?;
    let guard = paths
        .io_lock
        .lock()
        .map_err(|_| "event log lock poisoned".to_string())?;
    let prior = read_events_unlocked(paths)
        .map_err(|error| format!("authoritative persistence failure: {error}"))?;
    if let Some(event) = match_submission(&prior, &command, &submission)? {
        return Ok(CommittedApply {
            event: event.clone(),
            world_saved: true,
            degraded_cause: None,
            duplicate: true,
        });
    }
    let mut candidate = world.clone();
    let mut event = candidate.apply_command(command)?;
    event.submission = Some(SubmissionMetadata {
        schema_version: "monad.command-submission.v1".to_string(),
        idempotency_key: submission.idempotency_key,
        principal_id: submission.principal_id,
        principal_scope: submission.principal_scope,
        command_digest: digest,
    });
    append_event_unlocked(paths, &event)
        .map_err(|error| format!("authoritative persistence failure: {error}"))?;
    drop(guard);
    *world = candidate;
    match save_world(paths, world) {
        Ok(()) => Ok(CommittedApply {
            event,
            world_saved: true,
            degraded_cause: None,
            duplicate: false,
        }),
        Err(error) => Ok(CommittedApply {
            event,
            world_saved: false,
            degraded_cause: Some(format!("world save failed after durable commit: {error}")),
            duplicate: false,
        }),
    }
}

/// Restore current state from world.json plus any durable command-log tail.
/// A world ahead of its authoritative log is incoherent and fails closed.
pub fn restore_authoritative_world(paths: &StorePaths) -> Result<World, String> {
    let mut world = load_world(paths)?;
    let events = read_events(paths)?;
    validate_event_log(paths, &events)?;
    let durable_sequence = events.last().map(|event| event.sequence).unwrap_or(0);
    if world.event_sequence > durable_sequence {
        return Err(format!(
            "world sequence {} is ahead of durable command sequence {}",
            world.event_sequence, durable_sequence
        ));
    }
    let world_sequence = world.event_sequence;
    for event in events
        .iter()
        .filter(|event| event.sequence > world_sequence)
    {
        world.replay_event(event)?;
    }
    Ok(world)
}

pub fn validate_event_log(paths: &StorePaths, events: &[Event]) -> Result<World, String> {
    let mut submission_keys = std::collections::HashSet::new();
    for (index, event) in events.iter().enumerate() {
        let expected = index as u64 + 1;
        if event.sequence != expected {
            return Err(format!(
                "command log is non-contiguous: expected sequence {expected}, found {}",
                event.sequence
            ));
        }
        if let Some(metadata) = &event.submission {
            if !submission_keys.insert(metadata.idempotency_key.clone()) {
                return Err(format!(
                    "duplicate authoritative idempotency key '{}'",
                    metadata.idempotency_key
                ));
            }
            SubmissionContext {
                idempotency_key: metadata.idempotency_key.clone(),
                principal_id: metadata.principal_id.clone(),
                principal_scope: metadata.principal_scope.clone(),
            }
            .validate()?;
            if metadata.command_digest != command_digest(&event.command)? {
                return Err(format!(
                    "command digest mismatch at sequence {}",
                    event.sequence
                ));
            }
        }
    }
    let mut replayed = load_seed(paths)?;
    for event in events {
        replayed.replay_event(event)?;
    }
    Ok(replayed)
}

#[derive(serde::Deserialize)]
struct MigrationMarker {
    schema_version: String,
    completed: bool,
    world_id: String,
}

pub fn require_v2_migration_marker(
    paths: &StorePaths,
    world: &World,
    events: &[Event],
) -> Result<(), String> {
    let has_legacy = events
        .iter()
        .any(|event| event.schema_version != "monad.fleetcore.event.v2")
        || world.vessel_events.len()
            > events
                .iter()
                .map(|event| event.vessel_events.len())
                .sum::<usize>();
    if !has_legacy {
        return Ok(());
    }
    let raw = fs::read_to_string(&paths.migration_marker_path).map_err(|error| {
        format!("legacy vessel history requires explicit V2 migration marker: {error}")
    })?;
    let marker: MigrationMarker = serde_json::from_str(&raw)
        .map_err(|error| format!("invalid V2 migration marker: {error}"))?;
    if marker.schema_version != "monad.vessel-event-migration.v2"
        || !marker.completed
        || marker.world_id != world.world_id
    {
        return Err("invalid or incomplete V2 migration marker".to_string());
    }
    Ok(())
}

pub fn read_events(paths: &StorePaths) -> Result<Vec<Event>, String> {
    let _guard = paths
        .io_lock
        .lock()
        .map_err(|_| "event log lock poisoned".to_string())?;
    read_events_unlocked(paths)
}

fn read_events_unlocked(paths: &StorePaths) -> Result<Vec<Event>, String> {
    if !paths.events_path.exists() {
        return Ok(Vec::new());
    }
    let file = File::open(&paths.events_path)
        .map_err(|err| format!("failed to open {}: {err}", paths.events_path.display()))?;
    let reader = BufReader::new(file);
    let mut events = Vec::new();
    for (index, line) in reader.lines().enumerate() {
        let line = line.map_err(|err| format!("failed to read event line {}: {err}", index + 1))?;
        if line.trim().is_empty() {
            continue;
        }
        let event = serde_json::from_str(&line)
            .map_err(|err| format!("failed to parse event line {}: {err}", index + 1))?;
        events.push(event);
    }
    Ok(events)
}

pub fn replay_from_seed(paths: &StorePaths) -> Result<World, String> {
    let mut world = load_seed(paths)?;
    for event in read_events(paths)? {
        world.replay_event(&event)?;
    }
    Ok(world)
}

pub fn replay_from_latest_checkpoint(
    paths: &StorePaths,
    target_sequence: u64,
) -> Result<Option<CheckpointReplay>, String> {
    if !paths.checkpoints_dir.exists() {
        return Ok(None);
    }

    let mut checkpoints = fs::read_dir(&paths.checkpoints_dir)
        .map_err(|err| err.to_string())?
        .filter_map(Result::ok)
        .map(|entry| entry.path())
        .filter(|path| {
            path.extension()
                .is_some_and(|extension| extension == "json")
        })
        .collect::<Vec<_>>();
    checkpoints.sort_by(|left, right| right.file_name().cmp(&left.file_name()));

    let events = read_events(paths)?;
    for checkpoint_path in checkpoints {
        let mut world = load_world_from(&checkpoint_path)?;
        if world.event_sequence >= target_sequence {
            continue;
        }
        let checkpoint_sequence = world.event_sequence;
        let tail = events
            .iter()
            .filter(|event| {
                event.sequence > checkpoint_sequence && event.sequence <= target_sequence
            })
            .collect::<Vec<_>>();
        for event in &tail {
            world.replay_event(event)?;
        }
        if world.event_sequence != target_sequence {
            return Err(format!(
                "checkpoint replay ended at sequence {}, expected {}",
                world.event_sequence, target_sequence
            ));
        }
        return Ok(Some(CheckpointReplay {
            world,
            checkpoint_path,
            replayed_events: tail.len(),
        }));
    }
    Ok(None)
}

fn write_json<T: serde::Serialize>(path: &Path, value: &T) -> Result<(), String> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|err| err.to_string())?;
    }
    let tmp = path.with_extension("tmp");
    let json = serde_json::to_string_pretty(value).map_err(|err| err.to_string())?;
    fs::write(&tmp, format!("{json}\n"))
        .map_err(|err| format!("failed to write {}: {err}", tmp.display()))?;
    fs::rename(&tmp, path).map_err(|err| format!("failed to replace {}: {err}", path.display()))
}
