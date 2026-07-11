use fleetcore::command::Command;
use fleetcore::persistence::{
    append_event, ensure_dirs, load_seed, load_world, read_events, replay_from_seed,
    save_checkpoint, save_world, write_snapshot, StorePaths,
};
use fleetcore::snapshot::snapshot_json;
use fleetcore::vessel::Position;
use std::env;
use std::path::PathBuf;

const DEFAULT_STATE_DIR: &str = "data/fleetcore";
const DEFAULT_SEED_PATH: &str = "fleetcore/data/seed-world.json";

fn main() {
    if let Err(error) = run() {
        eprintln!("fleetcore: {error}");
        std::process::exit(1);
    }
}

fn run() -> Result<(), String> {
    let mut args: Vec<String> = env::args().skip(1).collect();
    if args.is_empty() || args[0] == "help" || args[0] == "--help" {
        print_help();
        return Ok(());
    }

    let state_dir =
        take_option(&mut args, "--state-dir").unwrap_or_else(|| DEFAULT_STATE_DIR.to_string());
    let seed_path =
        take_option(&mut args, "--seed").unwrap_or_else(|| DEFAULT_SEED_PATH.to_string());
    let paths = StorePaths::new(state_dir, seed_path);
    let command = args.remove(0);

    match command.as_str() {
        "init" => cmd_init(&paths),
        "inspect" => cmd_inspect(&paths),
        "snapshot" => {
            let output = args.first().map(PathBuf::from);
            let world = load_world(&paths)?;
            let path = write_snapshot(&paths, &world, output.as_deref())?;
            println!("snapshot written: {}", path.display());
            Ok(())
        }
        "replay" => cmd_replay(&paths),
        "step" | "run" => {
            let ticks = parse_u64(args.first(), "ticks")?;
            apply_and_persist(&paths, Command::Step { ticks })
        }
        "pause" => apply_and_persist(&paths, Command::PauseClock),
        "resume" => apply_and_persist(&paths, Command::ResumeClock),
        "set-time-scale" => {
            let scale = parse_u32(args.first(), "scale")?;
            apply_and_persist(&paths, Command::SetTimeScale { scale })
        }
        "set-route" => {
            if args.len() < 3 || args.len().is_multiple_of(2) {
                return Err(
                    "usage: fleetcore set-route <vessel-id> <lat> <lng> [<lat> <lng> ...]"
                        .to_string(),
                );
            }
            let vessel_id = args[0].clone();
            let mut route = Vec::new();
            for pair in args[1..].chunks(2) {
                route.push(Position {
                    lat: parse_f64(Some(&pair[0]), "lat")?,
                    lng: parse_f64(Some(&pair[1]), "lng")?,
                });
            }
            apply_and_persist(&paths, Command::SetRoute { vessel_id, route })
        }
        "spawn-contact" => {
            if args.len() != 7 {
                return Err("usage: fleetcore spawn-contact <id> <name> <callsign> <lat> <lng> <course> <speed-mps>".to_string());
            }
            apply_and_persist(
                &paths,
                Command::SpawnPassiveContact {
                    id: args[0].clone(),
                    name: args[1].clone(),
                    callsign: args[2].clone(),
                    position: Position {
                        lat: parse_f64(args.get(3), "lat")?,
                        lng: parse_f64(args.get(4), "lng")?,
                    },
                    course: parse_f64(args.get(5), "course")?,
                    speed_mps: parse_f64(args.get(6), "speed-mps")?,
                },
            )
        }
        "record-watch-event" => {
            if args.is_empty() {
                return Err("usage: fleetcore record-watch-event <message>".to_string());
            }
            apply_and_persist(
                &paths,
                Command::RecordWatchEvent {
                    message: args.join(" "),
                },
            )
        }
        _ => Err(format!(
            "unknown command '{command}'. Run `fleetcore help`."
        )),
    }
}

fn cmd_init(paths: &StorePaths) -> Result<(), String> {
    ensure_dirs(paths)?;
    let world = load_seed(paths)?;
    save_world(paths, &world)?;
    std::fs::write(&paths.events_path, "").map_err(|err| err.to_string())?;
    save_checkpoint(paths, &world)?;
    write_snapshot(paths, &world, None)?;
    println!("initialized world: {}", paths.world_path.display());
    Ok(())
}

fn cmd_inspect(paths: &StorePaths) -> Result<(), String> {
    let world = load_world(paths)?;
    println!("{}", snapshot_json(&world).map_err(|err| err.to_string())?);
    Ok(())
}

fn cmd_replay(paths: &StorePaths) -> Result<(), String> {
    let current = load_world(paths)?;
    let replayed = replay_from_seed(paths)?;
    let current_json = snapshot_json(&current).map_err(|err| err.to_string())?;
    let replayed_json = snapshot_json(&replayed).map_err(|err| err.to_string())?;
    if current_json != replayed_json {
        return Err(
            "replay mismatch: current world snapshot differs from seed plus events".to_string(),
        );
    }
    println!(
        "replay matched: {} events, tick {}",
        read_events(paths)?.len(),
        replayed.clock.tick
    );
    Ok(())
}

fn apply_and_persist(paths: &StorePaths, command: Command) -> Result<(), String> {
    let mut world = load_world(paths)?;
    let event = world.apply_command(command)?;
    append_event(paths, &event)?;
    save_world(paths, &world)?;
    save_checkpoint(paths, &world)?;
    write_snapshot(paths, &world, None)?;
    println!("{} at tick {}", event.event_type, event.tick);
    Ok(())
}

fn take_option(args: &mut Vec<String>, name: &str) -> Option<String> {
    if let Some(index) = args.iter().position(|arg| arg == name) {
        args.remove(index);
        if index < args.len() {
            Some(args.remove(index))
        } else {
            None
        }
    } else {
        None
    }
}

fn parse_u64(value: Option<&String>, name: &str) -> Result<u64, String> {
    value
        .ok_or_else(|| format!("missing {name}"))?
        .parse::<u64>()
        .map_err(|err| format!("invalid {name}: {err}"))
}

fn parse_u32(value: Option<&String>, name: &str) -> Result<u32, String> {
    value
        .ok_or_else(|| format!("missing {name}"))?
        .parse::<u32>()
        .map_err(|err| format!("invalid {name}: {err}"))
}

fn parse_f64(value: Option<&String>, name: &str) -> Result<f64, String> {
    value
        .ok_or_else(|| format!("missing {name}"))?
        .parse::<f64>()
        .map_err(|err| format!("invalid {name}: {err}"))
}

fn print_help() {
    println!(
        "FleetCore v1 deterministic local world prototype\n\n\
Usage:\n\
  fleetcore [--state-dir <path>] [--seed <path>] <command>\n\n\
Commands:\n\
  init\n\
  inspect\n\
  step <ticks>\n\
  run <ticks>\n\
  pause\n\
  resume\n\
  set-time-scale <scale>\n\
  set-route <vessel-id> <lat> <lng> [<lat> <lng> ...]\n\
  spawn-contact <id> <name> <callsign> <lat> <lng> <course> <speed-mps>\n\
  record-watch-event <message>\n\
  snapshot [output-path]\n\
  replay\n"
    );
}
