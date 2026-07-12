use crate::vessel::Position;
use serde::{Deserialize, Serialize};

/// FleetCore had no concept of land at all until this module -- every
/// vessel was just a lat/lng point on open water. These five zones are
/// the same rough bounding boxes `toys/fleet-motion/app.js`'s client-side
/// `LAND_ZONES` already draws for its own (previously unenforced) local
/// hazard warning, kept as the same names and rectangles rather than
/// inventing a second, divergent geography. This is still a rough
/// approximation -- rectangular bounding boxes, not real coastline
/// polygons -- but it is now the authoritative one: World::apply_command
/// actually rejects commands that would place a vessel on land, which the
/// client-side version never did once talking to a real server (see
/// docs/architecture/fleetcore-api.md).
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct LandZone {
    pub name: String,
    pub south: f64,
    pub north: f64,
    pub west: f64,
    pub east: f64,
}

pub fn land_zones() -> Vec<LandZone> {
    vec![
        LandZone {
            name: "Iranian Coast".to_string(),
            south: 26.9,
            north: 27.75,
            west: 54.8,
            east: 57.4,
        },
        LandZone {
            name: "Qeshm Island".to_string(),
            south: 26.62,
            north: 26.98,
            west: 55.55,
            east: 56.25,
        },
        LandZone {
            name: "Legacy Island Box".to_string(),
            south: 27.02,
            north: 27.16,
            west: 56.36,
            east: 56.55,
        },
        LandZone {
            name: "Musandam Peninsula".to_string(),
            south: 25.45,
            north: 26.35,
            west: 56.0,
            east: 56.7,
        },
        LandZone {
            name: "UAE Coast".to_string(),
            south: 24.65,
            north: 25.85,
            west: 54.1,
            east: 56.3,
        },
    ]
}

/// Returns the first zone containing `position`, if any. A position can
/// only ever match one zone in the current hand-authored set (none of the
/// five boxes overlap), but this returns the first match rather than
/// assuming that invariant holds forever.
pub fn zone_containing(position: &Position) -> Option<LandZone> {
    land_zones().into_iter().find(|zone| {
        position.lat >= zone.south
            && position.lat <= zone.north
            && position.lng >= zone.west
            && position.lng <= zone.east
    })
}

pub fn is_on_land(position: &Position) -> bool {
    zone_containing(position).is_some()
}
