use crate::command::Command;
use crate::event::Event;
use crate::snapshot;
use crate::world::World;
use std::fs::{self, File, OpenOptions};
use std::io::{BufRead, BufReader, Write};
use std::path::{Path, PathBuf};

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
}

impl StorePaths {
    pub fn new(state_dir: impl Into<PathBuf>, seed_path: impl Into<PathBuf>) -> Self {
        let state_dir = state_dir.into();
        Self {
            world_path: state_dir.join("world.json"),
            events_path: state_dir.join("events.jsonl"),
            snapshots_dir: state_dir.join("snapshots"),
            checkpoints_dir: state_dir.join("checkpoints"),
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

/// Apply against a clone and publish the mutation only after its authoritative
/// command envelope has been appended. An append failure therefore leaves the
/// caller's readable World byte-for-byte unchanged.
pub fn apply_authoritative(
    paths: &StorePaths,
    world: &mut World,
    command: Command,
) -> Result<Event, String> {
    let mut candidate = world.clone();
    let event = candidate.apply_command(command)?;
    append_event(paths, &event)
        .map_err(|error| format!("authoritative persistence failure: {error}"))?;
    *world = candidate;
    save_world(paths, world)
        .map_err(|error| format!("authoritative persistence failure: {error}"))?;
    Ok(event)
}

/// Restore current state from world.json plus any durable command-log tail.
/// A world ahead of its authoritative log is incoherent and fails closed.
pub fn restore_authoritative_world(paths: &StorePaths) -> Result<World, String> {
    let mut world = load_world(paths)?;
    let events = read_events(paths)?;
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

pub fn read_events(paths: &StorePaths) -> Result<Vec<Event>, String> {
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
