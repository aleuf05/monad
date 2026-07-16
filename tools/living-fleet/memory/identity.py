"""Seed identity + bounded, gradual, attributable, reversible trait drift.

Seed identity (role, values, communication style, authority relationship,
initial tendencies) lives in seed_data/identity_seed.json -- deliberately
separate from tools/living-fleet/captains.json, which stays the untouched
FleetCore-facing roster format. On first touch of a captain, the seed is
copied into identity_traits.seed_json (frozen forever after) and its
initial_tendencies become the starting traits_json.

Trait drift is intentionally boring: every reflection can nudge a trait by
at most a small bounded amount, every nudge is logged with why, and nothing
is ever destructively overwritten -- a "correction" is just another logged,
bounded delta in the opposite direction. This is the direct mechanism behind
"no personality rewrite after one dramatic event."
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Optional

from . import store
from .models import DEFAULT_TRAIT_BOUNDS, now

SEED_PATH = Path(__file__).with_name("seed_data") / "identity_seed.json"

_seed_cache: Optional[dict] = None


def _load_seed_file() -> dict:
    global _seed_cache
    if _seed_cache is None:
        if SEED_PATH.exists():
            _seed_cache = json.loads(SEED_PATH.read_text())
        else:
            _seed_cache = {}
    return _seed_cache


def seed_for(captain_id: str, role: str = "") -> dict:
    seeds = _load_seed_file()
    if captain_id in seeds:
        return seeds[captain_id]
    # A captain with no authored seed entry still needs to function --
    # fall back to a neutral identity rather than raising, since FleetCore
    # may one day add a fourth captain this module doesn't know about yet.
    return {
        "role_summary": role or "Escort captain",
        "doctrine_reference": "docs/architecture/living-fleet-v0.1.md",
        "values_priorities": ["formation safety over speed", "explicit doctrine over improvisation"],
        "communication_style": "concise, tactical, understated",
        "authority_relationship": (
            "Lieutenant cgl issues intent; the captain proposes bounded postures, "
            "never overrides FleetCore validation."
        ),
        "initial_tendencies": {
            "caution": 0.5,
            "initiative": 0.5,
            "curiosity": 0.5,
            "humor": 0.2,
            "trust": 0.5,
            "uncertainty_tolerance": 0.5,
        },
    }


def ensure_identity(conn: sqlite3.Connection, captain_id: str, role: str = "", *, commit: bool = True) -> dict[str, Any]:
    existing = store.fetch_one(conn, "identity_traits", captain_id)
    if existing:
        return existing
    seed = seed_for(captain_id, role)
    row = {
        "captain_id": captain_id,
        "seed_json": seed,
        "traits_json": dict(seed.get("initial_tendencies", {})),
        "trait_bounds_json": DEFAULT_TRAIT_BOUNDS,
        "drift_log_json": [],
        "updated_at": now(),
    }
    store.insert(conn, "identity_traits", row, commit=commit)
    return store.fetch_one(conn, "identity_traits", captain_id)


def get_traits(conn: sqlite3.Connection, captain_id: str, role: str = "") -> dict[str, Any]:
    return ensure_identity(conn, captain_id, role)


def apply_trait_shift(
    conn: sqlite3.Connection,
    captain_id: str,
    proposed_shift: dict[str, float],
    reason: str,
    reflection_id: Optional[str] = None,
    *,
    commit: bool = True,
) -> dict[str, Any]:
    """Clamp each proposed delta, clamp the resulting value into bounds, log
    the change, and persist. Returns the updated identity_traits row.
    """
    identity = ensure_identity(conn, captain_id, commit=commit)
    traits = dict(identity["traits_json"])
    bounds = identity["trait_bounds_json"]
    drift_log = list(identity["drift_log_json"])
    at = now()

    for trait, proposed_delta in proposed_shift.items():
        if trait not in bounds:
            continue  # unknown trait name -- ignore rather than silently invent a new axis
        trait_bounds = bounds[trait]
        max_delta = trait_bounds.get("max_delta_per_reflection", 0.07)
        clamped_delta = max(-max_delta, min(max_delta, proposed_delta))
        current_value = traits.get(trait, 0.5)
        new_value = max(trait_bounds["min"], min(trait_bounds["max"], current_value + clamped_delta))
        applied_delta = new_value - current_value
        if applied_delta == 0.0:
            continue
        traits[trait] = new_value
        drift_log.append(
            {
                "at": at,
                "trait": trait,
                "delta": applied_delta,
                "reason": reason,
                "reflection_id": reflection_id,
            }
        )

    store.update(
        conn,
        "identity_traits",
        captain_id,
        {"traits_json": traits, "drift_log_json": drift_log, "updated_at": at},
        commit=commit,
    )
    return store.fetch_one(conn, "identity_traits", captain_id)


def apply_correction(
    conn: sqlite3.Connection,
    captain_id: str,
    trait_deltas: dict[str, float],
    reason: str,
) -> dict[str, Any]:
    """A correction is just another bounded, logged delta -- never a
    destructive overwrite of trait history.
    """
    return apply_trait_shift(conn, captain_id, trait_deltas, reason=f"correction: {reason}", reflection_id=None)
