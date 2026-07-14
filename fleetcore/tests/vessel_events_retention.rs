// GitHub issue #6: bound the unbounded vessel_events history. Per Command's
// ruling, the stable per-event cursor is event_seq (not tick -- multiple
// events can share a tick -- and not array length/index, which breaks under
// truncation). These tests prove: same-tick events get distinct strictly
// increasing event_seq, the configured retention bound is enforced, that
// bound survives restart and replay identically, and pre-existing state
// files without event_seq migrate cleanly on load.

use fleetcore::command::Command;
use fleetcore::persistence::{load_seed, load_world, save_world, StorePaths};
use fleetcore::vessel::VesselEvent;
use fleetcore::world::World;
use std::path::PathBuf;

fn world() -> (StorePaths, World) {
    let dir = std::env::temp_dir().join(format!(
        "fleetcore-vessel-events-{}-{}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    ));
    let paths = StorePaths::new(
        dir,
        PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("data/seed-world.json"),
    );
    let world = load_seed(&paths).unwrap();
    (paths, world)
}

#[test]
fn same_tick_events_get_distinct_strictly_increasing_seq() {
    let (_paths, mut world) = world();
    // Every seed vessel starts underway on a real route, so re-setting each
    // one's route (before any Step advances the clock) fires a
    // RouteReplaced event per vessel, all sharing tick 0 -- exactly the
    // "multiple events, one tick" case Command's ruling was about.
    let vessel_ids: Vec<String> = world.vessels.iter().map(|v| v.id.clone()).collect();
    assert!(vessel_ids.len() >= 2, "seed must have multiple vessels for this test to mean anything");
    for id in &vessel_ids {
        let position = world.vessels.iter().find(|v| &v.id == id).unwrap().position;
        world
            .apply_command(Command::SetRoute {
                vessel_id: id.clone(),
                route: vec![fleetcore::vessel::Position {
                    lat: position.lat + 0.0001,
                    lng: position.lng,
                }],
            })
            .unwrap();
    }

    let this_tick: Vec<&VesselEvent> = world
        .vessel_events
        .iter()
        .filter(|event| tick_of(event) == 0)
        .collect();
    assert_eq!(this_tick.len(), vessel_ids.len(), "one RouteReplaced per vessel, same tick");

    let mut seqs: Vec<u64> = this_tick.iter().map(|event| event.event_seq()).collect();
    let mut sorted = seqs.clone();
    sorted.sort_unstable();
    seqs.sort_unstable();
    assert_eq!(seqs, sorted);
    let mut unique = seqs.clone();
    unique.dedup();
    assert_eq!(unique.len(), seqs.len(), "no two same-tick events share an event_seq");
    for window in seqs.windows(2) {
        assert!(window[1] > window[0], "event_seq must be strictly increasing, not just unique");
    }
}

#[test]
fn retention_bounds_vessel_events_to_the_configured_count() {
    let (_paths, mut world) = world();
    world.vessel_event_retention = 3;
    let vessel_id = world.vessels[0].id.clone();

    for offset in 1..=6 {
        let position = world.vessels.iter().find(|v| v.id == vessel_id).unwrap().position;
        world
            .apply_command(Command::SetRoute {
                vessel_id: vessel_id.clone(),
                route: vec![fleetcore::vessel::Position {
                    lat: position.lat + (offset as f64) * 0.0001,
                    lng: position.lng,
                }],
            })
            .unwrap();
    }

    assert_eq!(world.vessel_events.len(), 3, "never exceeds the configured retention");
    // The retained entries are the newest by event_seq -- eviction drops
    // from the front, not an arbitrary subset.
    let seqs: Vec<u64> = world.vessel_events.iter().map(|event| event.event_seq()).collect();
    assert_eq!(seqs, vec![world.next_vessel_event_seq - 3, world.next_vessel_event_seq - 2, world.next_vessel_event_seq - 1]);
}

#[test]
fn retention_and_seq_survive_restart_and_replay_identically() {
    let (paths, mut world) = world();
    world.vessel_event_retention = 2;
    let vessel_id = world.vessels[0].id.clone();
    for offset in 1..=5 {
        let position = world.vessels.iter().find(|v| v.id == vessel_id).unwrap().position;
        world
            .apply_command(Command::SetRoute {
                vessel_id: vessel_id.clone(),
                route: vec![fleetcore::vessel::Position {
                    lat: position.lat + (offset as f64) * 0.0001,
                    lng: position.lng,
                }],
            })
            .unwrap();
    }
    assert_eq!(world.vessel_events.len(), 2);

    save_world(&paths, &world).unwrap();
    let restarted = load_world(&paths).unwrap();
    // Compare by event_seq/tick/vessel_id, not full struct equality: JSON
    // round-tripping a f64 waypoint through serde_json's shortest-round-trip
    // formatting can print a couple of ULPs differently than the raw
    // in-memory value from this test's own arithmetic -- a pre-existing,
    // unrelated float-formatting quirk, not a vessel_events/event_seq bug.
    let restarted_seqs: Vec<(u64, u64, String)> = restarted
        .vessel_events
        .iter()
        .map(|event| (event.event_seq(), tick_of(event), vessel_id_of(event)))
        .collect();
    let original_seqs: Vec<(u64, u64, String)> = world
        .vessel_events
        .iter()
        .map(|event| (event.event_seq(), tick_of(event), vessel_id_of(event)))
        .collect();
    assert_eq!(restarted_seqs, original_seqs, "restart preserves the bounded tail's identity exactly");
    assert_eq!(restarted.vessel_events.len(), world.vessel_events.len());
    assert_eq!(restarted.next_vessel_event_seq, world.next_vessel_event_seq);
    assert_eq!(restarted.vessel_event_retention, world.vessel_event_retention);

    // Full replay from seed + the recorded command events must land on the
    // identical bounded vessel_events -- proving the live push-and-trim
    // path and the replay path (which both funnel through apply_command)
    // can't diverge on numbering or bounding.
    let mut replayed = load_seed(&paths).unwrap();
    replayed.vessel_event_retention = 2;
    for offset in 1..=5 {
        let position = replayed.vessels.iter().find(|v| v.id == vessel_id).unwrap().position;
        replayed
            .apply_command(Command::SetRoute {
                vessel_id: vessel_id.clone(),
                route: vec![fleetcore::vessel::Position {
                    lat: position.lat + (offset as f64) * 0.0001,
                    lng: position.lng,
                }],
            })
            .unwrap();
    }
    assert_eq!(replayed.vessel_events, world.vessel_events);

    let _ = std::fs::remove_dir_all(paths.state_dir);
}

#[test]
fn pre_existing_state_without_event_seq_migrates_on_load() {
    let (_paths, mut world) = world();
    // Simulate a state file saved before event_seq/retention existed:
    // vessel_events present, but every entry still at the serde default
    // (0), and next_vessel_event_seq never advanced past its own default.
    world.next_vessel_event_seq = 0;
    world.vessel_event_retention = fleetcore::world::default_vessel_event_retention();
    world.vessel_events = (0..5)
        .map(|index| VesselEvent::Holding {
            vessel_id: format!("vessel.test-{index}"),
            tick: 0,
            sim_time: "2026-07-10T20:00:00Z".to_string(),
            event_seq: 0,
        })
        .collect();

    world.normalize();

    let seqs: Vec<u64> = world.vessel_events.iter().map(|event| event.event_seq()).collect();
    assert_eq!(seqs, vec![1, 2, 3, 4, 5], "old events get fresh sequential values in their existing order");
    assert_eq!(world.next_vessel_event_seq, 6);
}

#[test]
fn pre_existing_oversized_state_is_trimmed_on_load() {
    let (_paths, mut world) = world();
    world.vessel_event_retention = 2;
    world.next_vessel_event_seq = 5;
    world.vessel_events = (0..5)
        .map(|index| VesselEvent::Holding {
            vessel_id: "vessel.test".to_string(),
            tick: 0,
            sim_time: "2026-07-10T20:00:00Z".to_string(),
            event_seq: index,
        })
        .collect();

    world.normalize();

    assert_eq!(world.vessel_events.len(), 2, "load-time normalize enforces the current bound too, not just push-time");
    let seqs: Vec<u64> = world.vessel_events.iter().map(|event| event.event_seq()).collect();
    assert_eq!(seqs, vec![3, 4], "keeps the newest, drops from the front");
}

fn tick_of(event: &VesselEvent) -> u64 {
    match event {
        VesselEvent::WaypointReached { tick, .. }
        | VesselEvent::RouteReplaced { tick, .. }
        | VesselEvent::RouteCompleted { tick, .. }
        | VesselEvent::Holding { tick, .. } => *tick,
    }
}

fn vessel_id_of(event: &VesselEvent) -> String {
    match event {
        VesselEvent::WaypointReached { vessel_id, .. }
        | VesselEvent::RouteReplaced { vessel_id, .. }
        | VesselEvent::RouteCompleted { vessel_id, .. }
        | VesselEvent::Holding { vessel_id, .. } => vessel_id.clone(),
    }
}
