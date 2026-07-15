use fleetcore::command::Command;
use fleetcore::persistence::{load_seed, StorePaths};
use fleetcore::vessel::{EscortMode, VesselEvent};
use std::path::PathBuf;

fn seed_world() -> fleetcore::world::World {
    let paths = StorePaths::new(
        std::env::temp_dir().join("fleetcore-new-content-events-tests"),
        PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("data/seed-world.json"),
    );
    load_seed(&paths).expect("seed world loads")
}

#[test]
fn escort_mode_change_emits_one_event() {
    let mut world = seed_world();
    let before = world.vessel_events.len();
    world
        .apply_command(Command::SetEscortMode {
            mode: EscortMode::Tight,
        })
        .unwrap();
    let new_events: Vec<_> = world.vessel_events[before..].to_vec();
    assert_eq!(
        new_events.len(),
        1,
        "expected exactly one EscortStationChanged event, got {new_events:?}"
    );
    match &new_events[0] {
        VesselEvent::EscortStationChanged {
            old_mode, new_mode, ..
        } => {
            assert_eq!(*old_mode, EscortMode::Screen, "seed world defaults to Screen");
            assert_eq!(*new_mode, EscortMode::Tight);
        }
        other => panic!("expected EscortStationChanged, got {other:?}"),
    }
}

#[test]
fn setting_escort_mode_to_same_value_emits_nothing() {
    let mut world = seed_world();
    world
        .apply_command(Command::SetEscortMode {
            mode: EscortMode::Screen,
        })
        .unwrap();
    let before = world.vessel_events.len();
    world
        .apply_command(Command::SetEscortMode {
            mode: EscortMode::Screen,
        })
        .unwrap();
    assert_eq!(
        world.vessel_events.len(),
        before,
        "re-setting the same escort mode should not emit a duplicate event"
    );
}

fn count_at_fuel(world: &fleetcore::world::World, id: &str) -> f64 {
    world
        .vessels
        .iter()
        .find(|v| v.id == id)
        .unwrap()
        .fuel_fraction
}

#[test]
fn fuel_severity_crossing_emits_event() {
    // Escort-station-keeping produces a very high volume of routine
    // WaypointReached/RouteCompleted "arrival" events (each tick's target
    // is usually only meters away, so scouts "arrive" almost every tick --
    // see world.rs's per-tick escort re-targeting) -- ~2.8-3 events/tick
    // per the retention constant's own doc comment. That fills the default
    // 2000-entry retention within a few thousand ticks, trimming out any
    // earlier fuel crossing long before a multi-thousand-tick Step
    // finishes. Rather than fighting that with a bigger retention value
    // (which also blows up runtime -- confirmed: retention=500_000 over
    // 200_000 ticks took minutes, not seconds, a real scaling question for
    // another day), set fuel_fraction just above a threshold directly and
    // step only far enough to cross it -- exercises the same crossing
    // logic without needing retention/runtime tradeoffs at all.
    let mut world = seed_world();
    for vessel in &mut world.vessels {
        if vessel.id == "vessel.scout-alpha" {
            vessel.fuel_fraction = 0.301;
        }
    }
    world.apply_command(Command::Step { ticks: 50 }).unwrap();
    assert!(
        count_at_fuel(&world, "vessel.scout-alpha") < 0.3,
        "sanity check: fuel should have crossed 0.3 within 50 ticks"
    );
    let crossings: Vec<_> = world
        .vessel_events
        .iter()
        .filter(|event| matches!(event, VesselEvent::FuelStatusChanged { .. }))
        .collect();
    assert!(
        !crossings.is_empty(),
        "expected a FuelStatusChanged event when fuel_fraction crosses the elevated threshold"
    );
    for event in &crossings {
        if let VesselEvent::FuelStatusChanged {
            old_severity,
            new_severity,
            vessel_id,
            ..
        } = event
        {
            assert_eq!(vessel_id, "vessel.scout-alpha");
            assert_eq!(old_severity, "routine");
            assert_eq!(new_severity, "elevated");
        }
    }
}

#[test]
fn fuel_severity_matches_documented_thresholds() {
    assert_eq!(fleetcore::vessel::fuel_severity(1.0), "routine");
    assert_eq!(fleetcore::vessel::fuel_severity(0.3), "elevated");
    assert_eq!(fleetcore::vessel::fuel_severity(0.31), "routine");
    assert_eq!(fleetcore::vessel::fuel_severity(0.15), "critical");
    assert_eq!(fleetcore::vessel::fuel_severity(0.16), "elevated");
    assert_eq!(fleetcore::vessel::fuel_severity(0.0), "critical");
}
