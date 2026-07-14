-- Effort B: Captain Memory & Identity storage contract.
--
-- One shared SQLite file (data/living-fleet/memory.db) serves all captains,
-- multi-tenant via a captain_id column on every table. captain_id='fleet' is
-- a reserved sentinel for genuinely shared, fleet-wide facts/narrative (see
-- episodic_memories/narrative_memories below) -- beliefs, procedural
-- lessons, relationships, and identity traits are always captain-scoped and
-- never use that sentinel, since those are one captain's own judgment.
--
-- Doctrine (docs/logging-doctrine.md, "Vector Space is Disposable"): this
-- database is the source of truth. embedding_json columns are a derived,
-- regenerable accelerator only, never authoritative.

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS schema_meta (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

-- Every ingested item (event/decision/conversation) lands here first,
-- regardless of eventual disposition -- an audit trail even for discards.
CREATE TABLE IF NOT EXISTS events (
  event_id              TEXT PRIMARY KEY,
  captain_id             TEXT NOT NULL,
  kind                    TEXT NOT NULL,             -- 'event' | 'decision' | 'conversation'
  category                 TEXT,                     -- 'telemetry','near-collision','mission-complete','lt-message',...
  occurred_at                TEXT NOT NULL,           -- sim_time / wall-clock ISO string, source clock
  observed_tick                 INTEGER,
  recorded_at                     REAL NOT NULL,      -- wall-clock ingestion time
  who_json                          TEXT,             -- JSON list of participant ids
  summary                             TEXT NOT NULL,
  payload_json                          TEXT,         -- raw source structure (evidence)
  source                                  TEXT NOT NULL, -- 'fleetcore-decision'|'fleetcore-snapshot'|'lieutenant-conversation'|'seed-import'
  salience_score                           REAL NOT NULL,
  salience_factors_json                       TEXT NOT NULL,
  disposition                                   TEXT NOT NULL, -- 'discard'|'summarize'|'episodic'|'episodic+reflect'
  episodic_id                                     TEXT REFERENCES episodic_memories(episodic_id)
);
CREATE INDEX IF NOT EXISTS idx_events_captain_time ON events(captain_id, occurred_at);

CREATE TABLE IF NOT EXISTS episodic_memories (
  episodic_id                    TEXT PRIMARY KEY,
  captain_id                      TEXT NOT NULL,       -- or 'fleet' for shared facts
  source_event_id                   TEXT REFERENCES events(event_id),
  occurred_at                          TEXT NOT NULL,
  who_json                                TEXT,
  what                                      TEXT NOT NULL, -- the fact of what happened
  outcome                                     TEXT,
  evidence_json                                 TEXT NOT NULL, -- source pointers: decision_id, mission_id, tick range, file refs
  certainty                                       REAL NOT NULL DEFAULT 1.0,
  interpretation                                    TEXT,       -- current sense-making, distinct from "what"
  interpretation_history_json                         TEXT NOT NULL DEFAULT '[]', -- [{interpretation,at,reason,reflection_id}]
  salience_score                                        REAL NOT NULL,
  strength                                                REAL NOT NULL DEFAULT 1.0, -- reinforced/decayed by reflection
  tags_json                                                 TEXT,
  influenced_decisions_json                                   TEXT NOT NULL DEFAULT '[]',
  is_imported_history                                           INTEGER NOT NULL DEFAULT 0,
  embedding_json                                                  TEXT, -- local TF-IDF sparse vector, regenerable
  created_at                                                        REAL NOT NULL,
  updated_at                                                          REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_episodic_captain_time     ON episodic_memories(captain_id, occurred_at);
CREATE INDEX IF NOT EXISTS idx_episodic_captain_salience ON episodic_memories(captain_id, salience_score);

CREATE TABLE IF NOT EXISTS semantic_beliefs (
  belief_id                 TEXT PRIMARY KEY,
  captain_id                  TEXT NOT NULL,
  subject                       TEXT NOT NULL,        -- 'captain.bravo' | 'doctrine.postures' | 'lieutenant.cgl'
  statement                      TEXT NOT NULL,
  belief_type                      TEXT NOT NULL,     -- 'fact' | 'doctrine' | 'belief'
  confidence                         REAL NOT NULL,
  evidence_json                        TEXT NOT NULL, -- [{episodic_id|event_id, weight}]
  provenance                             TEXT NOT NULL, -- 'observed'|'imported-history'|'reflection'|'told-by-lieutenant'
  status                                   TEXT NOT NULL DEFAULT 'active', -- 'active'|'superseded'|'retracted'
  supersedes_belief_id                       TEXT REFERENCES semantic_beliefs(belief_id),
  superseded_by_belief_id                      TEXT REFERENCES semantic_beliefs(belief_id),
  revision_reason                                TEXT,
  created_at                                       REAL NOT NULL,
  updated_at                                         REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_beliefs_captain_subject ON semantic_beliefs(captain_id, subject, status);

CREATE TABLE IF NOT EXISTS procedural_lessons (
  lesson_id          TEXT PRIMARY KEY,
  captain_id           TEXT NOT NULL,
  situation              TEXT NOT NULL,
  guidance                 TEXT NOT NULL,
  confidence                  REAL NOT NULL,
  evidence_json                 TEXT NOT NULL,
  status                          TEXT NOT NULL DEFAULT 'active',
  times_reinforced                   INTEGER NOT NULL DEFAULT 1,
  created_at                            REAL NOT NULL,
  updated_at                               REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_procedural_captain ON procedural_lessons(captain_id, status);

CREATE TABLE IF NOT EXISTS relationships (
  relationship_id       TEXT PRIMARY KEY,
  captain_id              TEXT NOT NULL,
  other_id                  TEXT NOT NULL,     -- 'lieutenant.cgl' | 'captain.bravo' | 'crew.engineering'
  trust                       REAL NOT NULL DEFAULT 0.5,
  friction                      REAL NOT NULL DEFAULT 0.0,
  history_summary                 TEXT,
  last_interaction_at                TEXT,
  interaction_count                     INTEGER NOT NULL DEFAULT 0,
  evidence_json                            TEXT,
  updated_at                                  REAL NOT NULL,
  UNIQUE(captain_id, other_id)
);

CREATE TABLE IF NOT EXISTS narrative_memories (
  narrative_id              TEXT PRIMARY KEY,
  captain_id                  TEXT NOT NULL,    -- or 'fleet'
  title                         TEXT NOT NULL,
  fact_ref_episodic_id            TEXT REFERENCES episodic_memories(episodic_id),
  fact_summary                       TEXT NOT NULL, -- sober, authoritative
  mythology                            TEXT NOT NULL, -- embellished/cultural retelling
  tags_json                               TEXT,
  is_imported_history                       INTEGER NOT NULL DEFAULT 0,
  created_at                                  REAL NOT NULL,
  updated_at                                    REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS reflections (
  reflection_id                TEXT PRIMARY KEY,
  captain_id                     TEXT NOT NULL,
  triggered_by                     TEXT NOT NULL, -- mission-completion|high-salience-event|repeated-similar-outcomes|
                                                   -- conflicting-memories|major-failure|major-success|scheduled|explicit-request
  period_start                       TEXT,
  period_end                            TEXT,
  summary                                  TEXT NOT NULL,
  patterns_json                              TEXT,
  belief_revisions_json                        TEXT,
  procedural_lessons_json                        TEXT,
  relationship_updates_json                        TEXT,
  memory_strength_changes_json                       TEXT,
  trait_shift_proposal_json                            TEXT,
  trait_shift_applied                                    INTEGER NOT NULL DEFAULT 0,
  provider                                                 TEXT NOT NULL, -- 'heuristic-reflection-v1'|'command:<name>'
  evidence_json                                              TEXT NOT NULL,
  created_at                                                   REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_reflections_captain ON reflections(captain_id, created_at);

CREATE TABLE IF NOT EXISTS identity_traits (
  captain_id          TEXT PRIMARY KEY,
  seed_json             TEXT NOT NULL,  -- immutable snapshot: role, values, comm style, authority relationship
  traits_json             TEXT NOT NULL, -- current revisable tendencies
  trait_bounds_json          TEXT NOT NULL,
  drift_log_json               TEXT NOT NULL DEFAULT '[]', -- append-only [{at,trait,delta,reason,reflection_id}]
  updated_at                     REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS corrections (
  correction_id      TEXT PRIMARY KEY,
  captain_id           TEXT NOT NULL,
  target_table           TEXT NOT NULL,  -- any table name above, incl. 'identity_traits'
  target_id                 TEXT NOT NULL,
  action                       TEXT NOT NULL, -- 'retract' | 'correct'
  reason                         TEXT NOT NULL,
  before_json                       TEXT,
  after_json                          TEXT,
  requested_by                          TEXT NOT NULL, -- 'lieutenant.cgl' | 'operator' | 'system'
  created_at                               REAL NOT NULL
);
