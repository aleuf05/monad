use fleetcore::command::Command;
use fleetcore::persistence::{load_seed, StorePaths};
use std::path::PathBuf;

fn seed_world() -> fleetcore::world::World {
    let paths = StorePaths::new(
        std::env::temp_dir().join("fleetcore-fuel-tests"),
        PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("data/seed-world.json"),
    );
    load_seed(&paths).expect("seed world loads")
}

fn vessel_fuel<'a>(world: &'a fleetcore::world::World, id: &str) -> f64 {
    world
        .vessels
        .iter()
        .find(|v| v.id == id)
        .unwrap_or_else(|| panic!("vessel {id} not found"))
        .fuel_fraction
}

#[test]
fn fuel_starts_full() {
    let world = seed_world();
    for vessel in &world.vessels {
        assert_eq!(
            vessel.fuel_fraction, 1.0,
            "{} should start with a full tank",
            vessel.id
        );
    }
}

#[test]
fn fuel_depletes_while_underway() {
    let mut world = seed_world();
    let before = vessel_fuel(&world, "vessel.scout-alpha");
    world.apply_command(Command::Step { ticks: 200 }).unwrap();
    let after = vessel_fuel(&world, "vessel.scout-alpha");
    assert!(
        after < before,
        "fuel should deplete after stepping while underway: before={before} after={after}"
    );
}

#[test]
fn fuel_never_goes_negative() {
    let mut world = seed_world();
    // Enough ticks to exhaust a full tank many times over at this vessel's
    // cruising speed -- proves clamping, not just "still depleting slowly".
    world.apply_command(Command::Step { ticks: 200_000 }).unwrap();
    for vessel in &world.vessels {
        assert!(
            vessel.fuel_fraction >= 0.0,
            "{} fuel_fraction went negative: {}",
            vessel.id,
            vessel.fuel_fraction
        );
    }
}

#[test]
fn reset_fleet_restores_full_fuel() {
    let mut world = seed_world();
    world.apply_command(Command::Step { ticks: 50_000 }).unwrap();
    let drained = vessel_fuel(&world, "vessel.scout-alpha");
    assert!(drained < 1.0, "sanity check: fuel actually drained first");

    world.apply_command(Command::ResetFleet).unwrap();
    assert_eq!(
        vessel_fuel(&world, "vessel.scout-alpha"),
        1.0,
        "ResetFleet should restore a full tank"
    );
}
