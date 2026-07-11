use crate::event::Event;
use crate::snapshot;
use crate::world::World;
use std::fs::{self, File, OpenOptions};
use std::io::{BufRead, BufReader, Write};
use std::path::{Path, PathBuf};

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
    Ok(path)
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
    writeln!(file, "{json}").map_err(|err| format!("failed to append event: {err}"))
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
