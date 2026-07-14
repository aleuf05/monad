use fleetcore::agent::{DecisionOutcome, EscortPosture};
use fleetcore::command::Command;
use fleetcore::persistence::{load_seed, StorePaths};
use fleetcore::route::bearing_degrees;
use std::path::PathBuf;

fn seed_world() -> fleetcore::world::World {
    let paths = StorePaths::new(
        std::env::temp_dir().join("fleetcore-living-fleet-tests"),
        PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("data/seed-world.json"),
    );
    load_seed(&paths).expect("seed world loads")
}

fn alpha_intent(captain_id: &str, observed_sequence: u64) -> Command {
    Command::SubmitEscortIntent {
        captain_id: captain_id.to_string(),
        vessel_id: "vessel.scout-alpha".to_string(),
        posture: EscortPosture::AdvanceScreen,
        target_contact_id: None,
        objective: "Establish the forward screen.".to_string(),
        assessment: "Formation is stable and the forward sector is clear.".to_string(),
        observed_tick: 0,
        observed_event_sequence: observed_sequence,
        reconsider_at_tick: 120,
    }
}

#[test]
fn accepted_intent_is_translated_by_deterministic_patrol_logic() {
    let mut world = seed_world();
    assert_eq!(world.captain_controls.len(), 3);

    let event = world
        .apply_command(alpha_intent("captain.alpha", 0))
        .expect("structured intent is processed");
    assert_eq!(event.event_type, "escort-intent-accepted");
    assert_eq!(world.agent_decisions[0].outcome, DecisionOutcome::Accepted);

    world
        .apply_command(Command::Step { ticks: 1 })
        .expect("world advances");
    let intent = world
        .escort_intents
        .iter()
        .find(|intent| intent.vessel_id == "vessel.scout-alpha")
        .expect("accepted intent remains current");
    assert_eq!(intent.executed_tick, Some(1));
    assert!(intent.consequence.as_deref().unwrap().contains("forward"));
    assert_eq!(world.agent_decisions[0].executed_tick, Some(1));
    assert!(world.agent_decisions[0]
        .consequence
        .as_deref()
        .unwrap()
        .contains("forward"));

    let leader = world
        .vessels
        .iter()
        .find(|vessel| vessel.id == "vessel.monad")
        .unwrap();
    let alpha = world
        .vessels
        .iter()
        .find(|vessel| vessel.id == "vessel.scout-alpha")
        .unwrap();
    let target = alpha.route[0];
    let target_bearing = bearing_degrees(leader.position, target);
    let delta = ((target_bearing - leader.course + 540.0) % 360.0) - 180.0;
    assert!(delta.abs() < 20.0, "screen target should be ahead of Monad");
}

#[test]
fn wrong_captain_is_rejected_and_durably_recorded_without_intent() {
    let mut world = seed_world();
    let event = world
        .apply_command(alpha_intent("captain.bravo", 0))
        .expect("domain rejection is still a replayable command event");

    assert_eq!(event.event_type, "escort-intent-rejected");
    assert!(world.escort_intents.is_empty());
    assert_eq!(world.agent_decisions.len(), 1);
    assert_eq!(world.agent_decisions[0].outcome, DecisionOutcome::Rejected);
    assert!(world.agent_decisions[0].result.contains("cannot command"));
}

#[test]
fn disabled_captain_cannot_replace_safe_deterministic_fallback() {
    let mut world = seed_world();
    world
        .apply_command(Command::SetCaptainEnabled {
            vessel_id: "vessel.scout-alpha".to_string(),
            enabled: false,
        })
        .unwrap();
    world
        .apply_command(Command::SetEscortMode {
            mode: fleetcore::vessel::EscortMode::Loose,
        })
        .unwrap();
    let observed_sequence = world.event_sequence;
    let mut command = alpha_intent("captain.alpha", observed_sequence);
    if let Command::SubmitEscortIntent {
        observed_tick,
        reconsider_at_tick,
        ..
    } = &mut command
    {
        *observed_tick = world.clock.tick;
        *reconsider_at_tick = world.clock.tick + 120;
    }
    let event = world.apply_command(command).unwrap();
    assert_eq!(event.event_type, "escort-intent-rejected");

    world.apply_command(Command::Step { ticks: 1 }).unwrap();
    let alpha = world
        .vessels
        .iter()
        .find(|vessel| vessel.id == "vessel.scout-alpha")
        .unwrap();
    assert_eq!(alpha.route.len(), 1, "legacy escort mode remains active");
}
