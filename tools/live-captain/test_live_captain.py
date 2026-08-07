"""Focused tests for the Live Captain minimum-context bootstrap contract
(packet LIVE-CAPTAIN-MINIMUM-CONTEXT-BOOTSTRAP-0.1 section 14). Tests the
new minimal contract only -- not a recreation of the parked legacy
experiment's test surface.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
import json
import hashlib
import sqlite3
import subprocess
import time
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from context_compiler import (
    ContextCompilerError,
    compact_runtime_sources,
    compile_live_captain_context,
    context_size_metrics,
    format_chronological_messages,
    load_required_text,
)
from persistence import (
    LiveCaptainStore,
    PersistenceError,
    load_admiral_attestation_read_only,
)
from run_tests import append_report, build_report
from server import LiveCaptainHandler, browser_sse_payload, load_context_sources
from auth import COOKIE_NAME, AuthConfig
from objectives import ObjectiveStore
from turn_arbiter import TurnArbiter
import generated_images
from context_metabolism import (
    ContinuityFact,
    LiteralKeyContract,
    PromotionPolicy,
    assess_literal_key_semantics,
    assess_candidate,
    audit_ledger,
    consolidate,
    contradictions,
    retire,
    retrieve,
    promotion_decision,
    ingest_attested_candidate,
)

# server's import of claude_daemon (tools/root-console) appends that
# directory to sys.path as a side effect; import it directly here too.
import claude_daemon  # noqa: E402


class _FakeStdin:
    def __init__(self, on_line):
        self._on_line = on_line

    def write(self, line):
        self._on_line(line)

    def flush(self):
        pass


class _FakeStdout:
    """Blocking line iterator fed by the test, standing in for the real
    `claude` subprocess's stdout pipe."""

    def __init__(self):
        self._queue: "__import__('queue').Queue[str | None]" = __import__("queue").Queue()

    def push(self, line):
        self._queue.put(line)

    def close(self):
        self._queue.put(None)

    def __iter__(self):
        return self

    def __next__(self):
        line = self._queue.get()
        if line is None:
            raise StopIteration
        return line


class _FakeProcess:
    def __init__(self, on_stdin_line):
        self.stdin = _FakeStdin(on_stdin_line)
        self.stdout = _FakeStdout()

    def poll(self):
        return None


class ClaudeDaemonConcurrencyTests(unittest.TestCase):
    """Regression test for the concurrency-stress-test finding (2026-08-02):
    two /api/turn requests arriving close together produced two identical
    persisted Captain replies. Root cause was `send_and_wait` subscribing
    to the broadcast stream *before* acquiring `_turn_lock`, so a waiting
    caller's queue silently accumulated another caller's completion events
    and returned them as its own. Fix: subscribe only after the lock is
    held, immediately before writing this call's own turn."""

    def _make_daemon(self):
        self.fake_process = None

        def fake_popen(*args, **kwargs):
            self.fake_process = _FakeProcess(self._on_stdin_line)
            return self.fake_process

        self.stdin_lines: list[str] = []
        self._stdin_lock = __import__("threading").Lock()

        with mock.patch.object(claude_daemon.subprocess, "Popen", side_effect=fake_popen):
            daemon = claude_daemon.ClaudeDaemon(cwd=Path("."))
        return daemon

    def _on_stdin_line(self, line):
        with self._stdin_lock:
            self.stdin_lines.append(line)

    def _push_reply(self, process, text):
        process.stdout.push(json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}))
        process.stdout.push(json.dumps({"type": "result", "is_error": False, "usage": {}}))

    def test_concurrent_turns_do_not_cross_deliver_replies(self):
        import threading
        import time

        daemon = self._make_daemon()
        process = self.fake_process

        a_write_seen = threading.Event()
        results: dict[str, dict] = {}
        errors: list[Exception] = []

        original_write_turn = daemon._write_turn

        def instrumented_write_turn(text):
            thread_id = original_write_turn(text)
            a_write_seen.set()
            return thread_id

        def run_a():
            try:
                daemon._write_turn = instrumented_write_turn
                results["a"] = daemon.send_and_wait("TURN-A")
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

        thread_a = threading.Thread(target=run_a)
        thread_a.start()
        self.assertTrue(a_write_seen.wait(timeout=2), "turn A was never written")

        # Turn A now holds _turn_lock and is blocked reading its own
        # completion events. Start turn B; under the fixed code it cannot
        # subscribe until it acquires the lock, so it must not see what we
        # broadcast next.
        thread_b = threading.Thread(target=lambda: results.__setitem__("b", daemon.send_and_wait("TURN-B")))
        thread_b.start()
        time.sleep(0.1)  # give B a chance to (incorrectly) subscribe early if the bug regresses

        self._push_reply(process, "REPLY-A")
        thread_a.join(timeout=2)
        self.assertFalse(thread_a.is_alive(), "turn A did not complete")

        self._push_reply(process, "REPLY-B")
        thread_b.join(timeout=2)
        self.assertFalse(thread_b.is_alive(), "turn B did not complete")

        self.assertFalse(errors, f"unexpected errors: {errors}")
        self.assertEqual(results["a"]["text"], "REPLY-A")
        self.assertEqual(results["b"]["text"], "REPLY-B")


class LedgerAuditTests(unittest.TestCase):
    def test_live_ledger_has_provenance_and_no_exact_duplicate_claims(self):
        ledger = (
            Path(__file__).resolve().parent / "context" / "continuity-ledger.md"
        ).read_text(encoding="utf-8")
        audit = audit_ledger(ledger)
        self.assertGreaterEqual(len(audit.entries), 10)
        self.assertEqual(audit.missing_source, ())
        self.assertEqual(audit.duplicate_assertions, ())

    def test_audit_reports_missing_source_and_duplicate_without_mutation(self):
        ledger = """## Durable commitments
- Keep the window. Source: commissioning
- Keep the window. Source: commissioning
- Unproven claim.
"""
        audit = audit_ledger(ledger)
        self.assertEqual(audit.missing_source, ("Unproven claim.",))
        self.assertEqual(audit.duplicate_assertions, ("keep the window.",))
        self.assertIn("Unproven claim.", ledger)


class ContextCompilerTests(unittest.TestCase):
    def test_hot_context_drops_archives_but_keeps_live_sections(self):
        bearing, ledger, channel = compact_runtime_sources(
            "old commissioning\n## Living Captain Master Page course, 2026-08-05\nLIVE COURSE",
            "# Continuity Ledger\n## Durable commitments\nKEEP\n## Verified state\nOLD RECEIPTS",
            "old dispatch\n---\nlatest dispatch",
        )
        self.assertNotIn("old commissioning", bearing)
        self.assertIn("LIVE COURSE", bearing)
        self.assertIn("KEEP", ledger)
        self.assertNotIn("OLD RECEIPTS", ledger)
        self.assertEqual(channel, "latest dispatch")

    def test_latest_operational_bearing_supersedes_commissioning_history(self):
        bearing, _, _ = compact_runtime_sources(
            "archive\n## Living Captain Master Page course, 2026-08-05\nOLD COURSE\n"
            "## Current operational bearing, 2026-08-06\nCURRENT COURSE",
            "LEDGER",
            "CHANNEL",
        )
        self.assertIn("CURRENT COURSE", bearing)
        self.assertNotIn("OLD COURSE", bearing)
        self.assertNotIn("archive", bearing)

    def test_kernel_and_bearing_always_included(self):
        text = compile_live_captain_context(
            "KERNEL-MARKER", "BEARING-MARKER", "LEDGER-MARKER", [], "hello captain"
        )
        self.assertIn("KERNEL-MARKER", text)
        self.assertIn("BEARING-MARKER", text)

    def test_missing_kernel_raises(self):
        with self.assertRaises(ContextCompilerError):
            compile_live_captain_context("", "BEARING-MARKER", "LEDGER", [], "hello")

    def test_missing_bearing_raises(self):
        with self.assertRaises(ContextCompilerError):
            compile_live_captain_context("KERNEL", "", "LEDGER", [], "hello")

    def test_missing_continuity_ledger_raises(self):
        with self.assertRaises(ContextCompilerError):
            compile_live_captain_context("KERNEL", "BEARING", "", [], "hello")

    def test_missing_current_message_raises(self):
        with self.assertRaises(ContextCompilerError):
            compile_live_captain_context("KERNEL", "BEARING", "LEDGER", [], "   ")

    def test_continuity_ledger_precedes_recent_conversation(self):
        text = compile_live_captain_context(
            "KERNEL", "BEARING", "LEDGER-MARKER", [], "hello"
        )
        self.assertLess(text.index("LEDGER-MARKER"), text.index("# Recent conversation"))

    def test_recent_messages_chronological_and_not_mode_filtered(self):
        # Messages from different "task types" (conceptual, design, code
        # review) all remain visible together, in order -- there is no
        # mode field anywhere in the schema to filter by.
        messages = [
            {"role": "admiral", "text": "let's talk concepts", "seq": 1, "ts": 1},
            {"role": "captain", "text": "sure, concept reply", "seq": 2, "ts": 2},
            {"role": "admiral", "text": "now review this diff", "seq": 3, "ts": 3},
            {"role": "captain", "text": "diff looks fine", "seq": 4, "ts": 4},
        ]
        formatted = format_chronological_messages(messages)
        positions = [formatted.index(m["text"]) for m in messages]
        self.assertEqual(positions, sorted(positions))

    def test_current_admiral_message_appears_once_and_last(self):
        text = compile_live_captain_context(
            "KERNEL", "BEARING", "LEDGER", [{"role": "admiral", "text": "earlier", "seq": 1, "ts": 1}],
            "THE CURRENT MESSAGE",
        )
        self.assertEqual(text.count("THE CURRENT MESSAGE"), 1)
        self.assertGreater(text.rindex("THE CURRENT MESSAGE"), text.index("earlier"))

    def test_command_draft_adds_immediate_implementation_contract(self):
        text = compile_live_captain_context(
            "KERNEL", "BEARING", "LEDGER", [], "Refit the bridge.", interaction_mode="command_draft"
        )
        self.assertIn("one coherent high-level command", text)
        self.assertIn("authorized for immediate implementation", text)
        self.assertLess(text.index("# Interaction contract"), text.index("# Current Admiral message"))

    def test_unknown_interaction_mode_is_rejected(self):
        with self.assertRaisesRegex(ContextCompilerError, "unsupported interaction mode"):
            compile_live_captain_context(
                "KERNEL", "BEARING", "LEDGER", [], "hello", interaction_mode="wishful_thinking"
            )

    def test_context_size_metrics_attribute_sources_and_total(self):
        messages = [{"role": "admiral", "text": "earlier"}]
        compiled = compile_live_captain_context(
            "KERNEL", "BEARING", "LEDGER", messages, "current"
        )
        metrics = context_size_metrics(
            "KERNEL", "BEARING", "LEDGER", messages, "current", compiled
        )
        self.assertEqual(metrics["kernel_chars"], 6)
        self.assertEqual(metrics["conversation_chars"], len("Admiral: earlier"))
        self.assertEqual(metrics["compiled_chars"], len(compiled))
        self.assertEqual(metrics["compiled_bytes"], len(compiled.encode("utf-8")))

    def test_omission_is_reported_not_hidden(self):
        formatted = format_chronological_messages(
            [{"role": "admiral", "text": "recent one", "seq": 31, "ts": 1}], omitted=12
        )
        self.assertIn("12 earlier message", formatted)

    def test_load_required_text_missing_file_raises(self):
        with self.assertRaises(ContextCompilerError):
            load_required_text(Path("/nonexistent/does-not-exist.md"), "test file")

    def test_load_required_text_empty_file_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            empty = Path(tmp) / "empty.md"
            empty.write_text("   \n")
            with self.assertRaises(ContextCompilerError):
                load_required_text(empty, "test file")


class ContextMetabolismTests(unittest.TestCase):
    def setUp(self):
        self.facts = [
            ContinuityFact("service.telemetry", "inactive", "turn-40"),
            ContinuityFact("service.telemetry", "active", "turn-44"),
            ContinuityFact("window.policy", "rolling verbatim", "commissioning"),
        ]

    def test_consolidation_removes_only_exact_duplicates(self):
        facts = self.facts + [self.facts[-1]]
        self.assertEqual(consolidate(facts), self.facts)

    def test_contradiction_detection_preserves_competing_provenance(self):
        conflict = contradictions(self.facts)["service.telemetry"]
        self.assertEqual([fact.source for fact in conflict], ["turn-40", "turn-44"])

    def test_retirement_resolves_conflict_without_erasing_history(self):
        updated = retire(self.facts, "service.telemetry", "inactive")
        self.assertNotIn("service.telemetry", contradictions(updated))
        historical = retrieve(updated, "service telemetry", include_retired=True)
        self.assertEqual([fact.status for fact in historical], ["retired", "active"])

    def test_retrieval_defaults_to_active_and_leaves_verbatim_input_untouched(self):
        original = list(self.facts)
        updated = retire(self.facts, "service.telemetry", "inactive")
        self.assertEqual([fact.value for fact in retrieve(updated, "telemetry")], ["active"])
        self.assertEqual(self.facts, original)

    def test_empty_or_unproven_fact_is_rejected(self):
        with self.assertRaises(ValueError):
            ContinuityFact("", "active", "turn-1")

    def test_real_candidate_update_is_classified_without_mutation(self):
        baseline = [
            ContinuityFact(
                "ledger.auto_edit",
                "disabled pending safe semantic contradiction handling",
                "continuity-ledger.md unresolved proofs",
            )
        ]
        original = list(baseline)
        candidate = ContinuityFact(
            "ledger.auto_edit",
            "enabled",
            "candidate commissioning update",
        )
        assessment = assess_candidate(baseline, candidate)
        self.assertEqual(assessment.disposition, "conflict")
        self.assertEqual(assessment.existing, tuple(baseline))
        self.assertEqual(baseline, original)

    def test_candidate_assessment_distinguishes_add_and_duplicate(self):
        duplicate = assess_candidate(self.facts, self.facts[-1])
        addition = assess_candidate(
            self.facts,
            ContinuityFact("conference.token", "Conference", "commissioning"),
        )
        self.assertEqual(duplicate.disposition, "duplicate")
        self.assertEqual(addition.disposition, "add")

    def test_promotion_boundary_defaults_closed_and_routes_conflict_to_human(self):
        addition = ContinuityFact("conference.token", "Conference", "turn-80")
        conflict = ContinuityFact("window.policy", "summary only", "turn-81")
        self.assertEqual(promotion_decision(self.facts, addition).action, "human_review")
        decision = promotion_decision(self.facts, conflict)
        self.assertEqual(decision.action, "human_review")
        self.assertIn("active keyed value conflicts", decision.reasons)

    def test_promotion_boundary_allows_only_explicit_novel_trusted_fact(self):
        policy = PromotionPolicy(
            allowed_keys=frozenset({"conference.token"}),
            trusted_source_prefixes=("verified-test:",),
        )
        candidate = ContinuityFact(
            "conference.token", "Conference", "verified-test:command-token"
        )
        decision = promotion_decision(self.facts, candidate, policy)
        self.assertEqual(decision.action, "promote")
        self.assertEqual(decision.assessment.disposition, "add")
        untrusted = ContinuityFact("conference.token", "Conference", "model-inference")
        self.assertEqual(
            promotion_decision(self.facts, untrusted, policy).action, "human_review"
        )

    def test_promotion_duplicate_is_no_op_even_without_write_authority(self):
        decision = promotion_decision(self.facts, self.facts[-1])
        self.assertEqual(decision.action, "no_op")
        self.assertEqual(decision.assessment.disposition, "duplicate")

    def test_promotion_rejects_allowlisted_key_with_contradictory_baseline(self):
        policy = PromotionPolicy(
            allowed_keys=frozenset({"service.telemetry"}),
            trusted_source_prefixes=("verified-test:",),
        )
        candidate = ContinuityFact(
            "service.telemetry", "degraded", "verified-test:health-check"
        )
        decision = promotion_decision(self.facts, candidate, policy)
        self.assertEqual(decision.action, "human_review")
        self.assertIn("baseline key is already contradictory", decision.reasons)

    def test_attested_candidate_ingestion_drives_representative_dry_run(self):
        evidence = b"Admiral command: Conference is the pause token"
        digest = hashlib.sha256(evidence).hexdigest()
        payload = json.dumps(
            {
                "schema": "live-captain-candidate/v2",
                "key": "conference.token",
                "value": "Conference",
                "evidence_ref": "command:157",
                "evidence_sha256": digest,
                "evidence_start": 17,
                "evidence_end": 27,
            }
        )
        candidate = ingest_attested_candidate(payload, {"command:157": evidence})
        policy = PromotionPolicy(
            allowed_keys=frozenset({"conference.token"}),
            trusted_source_prefixes=("attested:command:",),
        )
        addition = promotion_decision(self.facts, candidate, policy)
        duplicate = promotion_decision(self.facts + [candidate], candidate, policy)
        conflict = promotion_decision(
            self.facts + [ContinuityFact("conference.token", "Halt", "turn-1")],
            candidate,
            policy,
        )
        self.assertEqual(
            (addition.action, duplicate.action, conflict.action),
            ("promote", "no_op", "human_review"),
        )

    def test_candidate_ingestion_rejects_self_attestation_and_digest_mismatch(self):
        evidence = b"external command record"
        payload = json.dumps(
            {
                "schema": "live-captain-candidate/v2",
                "key": "conference.token",
                "value": "Conference",
                "evidence_ref": "command:157",
                "evidence_sha256": "0" * 64,
                "evidence_start": 0,
                "evidence_end": 8,
            }
        )
        with self.assertRaisesRegex(ValueError, "independently available"):
            ingest_attested_candidate(payload, {})
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            ingest_attested_candidate(payload, {"command:157": evidence})

    def test_candidate_ingestion_rejects_schema_drift(self):
        payload = json.dumps(
            {
                "schema": "live-captain-candidate/v2",
                "key": "conference.token",
                "value": "Conference",
                "evidence_ref": "command:157",
                "evidence_sha256": "0" * 64,
                "evidence_start": 0,
                "evidence_end": 8,
                "model_confidence": 1.0,
            }
        )
        with self.assertRaisesRegex(ValueError, "unknown or missing fields"):
            ingest_attested_candidate(payload, {})

    def test_persisted_admiral_command_attests_candidate_dry_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = LiveCaptainStore(Path(tmp) / "test.db")
            seq = store.record_message(
                "admiral", "Conference is the pause token", "kd", "bd", "ld"
            )
            evidence_ref, evidence = store.load_admiral_attestation(seq)
            payload = json.dumps(
                {
                    "schema": "live-captain-candidate/v2",
                    "key": "conference.token",
                    "value": "Conference",
                    "evidence_ref": evidence_ref,
                    "evidence_sha256": hashlib.sha256(evidence).hexdigest(),
                    "evidence_start": 0,
                    "evidence_end": 10,
                }
            )
            candidate = ingest_attested_candidate(payload, {evidence_ref: evidence})
            decision = promotion_decision(
                self.facts,
                candidate,
                PromotionPolicy(
                    allowed_keys=frozenset({"conference.token"}),
                    trusted_source_prefixes=("attested:message:admiral:",),
                ),
            )
            self.assertEqual(decision.action, "promote")

    def test_candidate_ingestion_binds_value_to_exact_evidence_span(self):
        evidence = "Admiral says: café is ready".encode("utf-8")
        base = {
            "schema": "live-captain-candidate/v2",
            "key": "studio.state",
            "value": "café",
            "evidence_ref": "command:span",
            "evidence_sha256": hashlib.sha256(evidence).hexdigest(),
            "evidence_start": 14,
            "evidence_end": 18,
        }
        candidate = ingest_attested_candidate(
            json.dumps(base), {"command:span": evidence}
        )
        self.assertEqual(candidate.value, "café")
        self.assertTrue(candidate.source.endswith("#chars:14-18"))

        forged = dict(base, value="done")
        with self.assertRaisesRegex(ValueError, "does not match"):
            ingest_attested_candidate(json.dumps(forged), {"command:span": evidence})

    def test_candidate_ingestion_rejects_invalid_evidence_span(self):
        evidence = b"Conference"
        payload = {
            "schema": "live-captain-candidate/v2",
            "key": "conference.token",
            "value": "Conference",
            "evidence_ref": "command:span",
            "evidence_sha256": hashlib.sha256(evidence).hexdigest(),
            "evidence_start": 0,
            "evidence_end": 99,
        }
        with self.assertRaisesRegex(ValueError, "out of range"):
            ingest_attested_candidate(json.dumps(payload), {"command:span": evidence})

    def test_literal_key_semantics_proves_only_declared_admiral_span(self):
        evidence = b"be bold Captain"
        payload = json.dumps(
            {
                "schema": "live-captain-candidate/v2",
                "key": "admiral.message.literal",
                "value": "be bold Captain",
                "evidence_ref": "message:admiral:218",
                "evidence_sha256": hashlib.sha256(evidence).hexdigest(),
                "evidence_start": 0,
                "evidence_end": len(evidence),
            }
        )
        candidate = ingest_attested_candidate(
            payload, {"message:admiral:218": evidence}
        )
        assessment = assess_literal_key_semantics(
            candidate, LiteralKeyContract("admiral.message.literal")
        )
        self.assertTrue(assessment.supported)
        self.assertIn("only the exact", assessment.reason)

    def test_literal_key_semantics_rejects_interpretive_key_and_source(self):
        contract = LiteralKeyContract("admiral.message.literal")
        interpreted = ContinuityFact(
            "commissioning.authorization.scope",
            "be bold Captain",
            "attested:message:admiral:218#sha256:digest#chars:0-15",
        )
        wrong_source = ContinuityFact(
            "admiral.message.literal",
            "be bold Captain",
            "attested:command:218#sha256:digest#chars:0-15",
        )
        self.assertFalse(assess_literal_key_semantics(interpreted, contract).supported)
        self.assertFalse(assess_literal_key_semantics(wrong_source, contract).supported)

    def test_captain_message_cannot_attest_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = LiveCaptainStore(Path(tmp) / "test.db")
            seq = store.record_message("captain", "Conference", "kd", "bd", "ld")
            with self.assertRaisesRegex(PersistenceError, "only persisted Admiral"):
                store.load_admiral_attestation(seq)

    def test_read_only_attestation_does_not_record_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            store = LiveCaptainStore(db_path)
            seq = store.record_message("admiral", "Keep the session light", "kd", "bd", "ld")
            restart_count = store.restart_count()
            store.close()

            evidence_ref, evidence = load_admiral_attestation_read_only(db_path, seq)

            self.assertEqual(evidence_ref, f"message:admiral:{seq}")
            self.assertEqual(evidence, b"Keep the session light")
            connection = sqlite3.connect(db_path)
            observed_count = connection.execute("SELECT COUNT(*) FROM restarts").fetchone()[0]
            connection.close()
            self.assertEqual(observed_count, restart_count)


class PersistenceTests(unittest.TestCase):
    def test_chronological_ordering_across_all_messages(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = LiveCaptainStore(Path(tmp) / "test.db")
            store.record_message("admiral", "first", "kd", "bd", "ld")
            store.record_message("captain", "second", "kd", "bd", "ld")
            store.record_message("admiral", "third", "kd", "bd", "ld")
            messages, omitted = store.load_recent_messages(limit=30)
            self.assertEqual([m["text"] for m in messages], ["first", "second", "third"])
            self.assertEqual(omitted, 0)
            store.close()

    def test_window_reports_omitted_older_messages(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = LiveCaptainStore(Path(tmp) / "test.db")
            for i in range(35):
                store.record_message("admiral", f"message-{i}", "kd", "bd", "ld")
            messages, omitted = store.load_recent_messages(limit=30)
            self.assertEqual(len(messages), 30)
            self.assertEqual(omitted, 5)
            self.assertEqual(messages[0]["text"], "message-5")
            self.assertEqual(messages[-1]["text"], "message-34")
            store.close()

    def test_invalid_role_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = LiveCaptainStore(Path(tmp) / "test.db")
            with self.assertRaises(PersistenceError):
                store.record_message("mode-harvest", "text", "kd", "bd", "ld")
            store.close()

    def test_empty_message_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = LiveCaptainStore(Path(tmp) / "test.db")
            with self.assertRaises(PersistenceError):
                store.record_message("admiral", "   ", "kd", "bd", "ld")
            store.close()

    def test_restart_marker_recorded_and_conversation_survives(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            store = LiveCaptainStore(db_path)
            store.record_message("admiral", "before restart", "kd", "bd", "ld")
            store.close()

            # Simulate a service restart: new process, same db file.
            restarted = LiveCaptainStore(db_path)
            messages, _ = restarted.load_recent_messages(limit=30)
            self.assertEqual(messages[0]["text"], "before restart")
            self.assertEqual(restarted.restart_count(), 2)
            restarted.close()

    def test_message_retains_all_context_source_digests(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = LiveCaptainStore(Path(tmp) / "test.db")
            store.record_message("admiral", "trace this", "kernel-1", "bearing-2", "ledger-3")
            messages, _ = store.load_recent_messages()
            self.assertEqual(messages[0]["kernel_digest"], "kernel-1")
            self.assertEqual(messages[0]["bearing_digest"], "bearing-2")
            self.assertEqual(messages[0]["ledger_digest"], "ledger-3")
            store.close()

    def test_existing_database_migrates_without_inventing_ledger_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "old.db"
            import sqlite3

            conn = sqlite3.connect(db_path)
            conn.executescript(
                """
                CREATE TABLE messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL, seq INTEGER NOT NULL,
                    role TEXT NOT NULL, text TEXT NOT NULL, ts REAL NOT NULL,
                    kernel_digest TEXT NOT NULL, bearing_digest TEXT NOT NULL
                );
                CREATE TABLE restarts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL, ts REAL NOT NULL
                );
                INSERT INTO messages
                    (session_id, seq, role, text, ts, kernel_digest, bearing_digest)
                VALUES ('old', 1, 'admiral', 'historical', 1, 'kd', 'bd');
                """
            )
            conn.commit()
            conn.close()

            store = LiveCaptainStore(db_path)
            messages, _ = store.load_recent_messages()
            self.assertEqual(messages[0]["ledger_digest"], "")
            store.record_message("captain", "current", "kd2", "bd2", "ld2")
            messages, _ = store.load_recent_messages()
            self.assertEqual(messages[-1]["ledger_digest"], "ld2")
            store.close()

    def test_malformed_persistence_path_fails_truthfully(self):
        # A db path under a file (not a directory) cannot be created;
        # this must raise, not silently fall back to in-memory state.
        with tempfile.TemporaryDirectory() as tmp:
            blocking_file = Path(tmp) / "not-a-directory"
            blocking_file.write_text("x")
            with self.assertRaises((PersistenceError, OSError, NotADirectoryError)):
                LiveCaptainStore(blocking_file / "live-captain.db")


class TestReportingTests(unittest.TestCase):
    def test_build_report_uses_exit_code_as_result(self):
        completed = subprocess.CompletedProcess(
            args=["python3", "-m", "unittest"],
            returncode=1,
            stdout="Ran 7 tests in 0.1s\n",
            stderr="FAILED (failures=1)\n",
        )
        report = build_report(list(completed.args), completed, 0.125)
        self.assertEqual(report["result"], "fail")
        self.assertEqual(report["tests_run"], 7)
        self.assertEqual(report["exit_code"], 1)

    def test_append_report_writes_one_json_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "test-runs.jsonl"
            append_report(path, {"result": "pass", "tests_run": 19})
            self.assertEqual(
                json.loads(path.read_text(encoding="utf-8")),
                {"result": "pass", "tests_run": 19},
            )


class BrowserStreamTests(unittest.TestCase):
    def test_generated_image_path_becomes_authenticated_url_in_sse(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Path(tmp)
            image = store / "thread" / "call.png"
            image.parent.mkdir(parents=True)
            image.write_bytes(b"\x89PNG\r\n\x1a\nimage")
            event = {
                "type": "codex_event",
                "params": {"item": {"path": str(image), "text": f"saved {image}"}},
            }
            with mock.patch.object(generated_images, "GENERATED_IMAGE_DIR", store):
                payload = browser_sse_payload(event).decode("utf-8")
            body = json.loads(payload.removeprefix("data: ").strip())
            self.assertTrue(
                body["params"]["item"]["path"].startswith(
                    generated_images.GENERATED_IMAGE_API_PREFIX
                )
            )
            self.assertEqual(body["params"]["item"]["text"], f"saved {image}")


class ContextSourceReloadTests(unittest.TestCase):
    def test_context_sources_reload_from_disk_without_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            kernel = root / "kernel.md"
            bearing = root / "bearing.md"
            ledger = root / "ledger.md"
            kernel.write_text("kernel-v1", encoding="utf-8")
            bearing.write_text("bearing-v1", encoding="utf-8")
            ledger.write_text("ledger-v1", encoding="utf-8")

            first = load_context_sources(kernel, bearing, ledger)
            ledger.write_text("ledger-v2", encoding="utf-8")
            second = load_context_sources(kernel, bearing, ledger)

            self.assertEqual(first["ledger_text"], "ledger-v1")
            self.assertEqual(second["ledger_text"], "ledger-v2")
            self.assertNotEqual(first["ledger_digest"], second["ledger_digest"])

    def test_context_source_reload_fails_closed_on_empty_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            kernel = root / "kernel.md"
            bearing = root / "bearing.md"
            ledger = root / "ledger.md"
            kernel.write_text("kernel", encoding="utf-8")
            bearing.write_text("bearing", encoding="utf-8")
            ledger.write_text("   ", encoding="utf-8")

            with self.assertRaises(ContextCompilerError):
                load_context_sources(kernel, bearing, ledger)


class EndToEndHttpBootTests(unittest.TestCase):

    """Closes the boot-audit gap named in
    docs/logs/2026-08-02-boot-process-audit.md: prior coverage was
    unit-level plus one historical live restart, never a test that actually
    starts this server and talks to it over a real HTTP socket. The Codex
    daemon is stubbed (subprocess spawn is not what this gap is about); the
    HTTP server, auth, and request/response wiring are all real."""

    class _FakeDaemon:
        def __init__(self):
            self.compiled = []
            self.broadcasts = []

        def send_and_wait(self, compiled_text, sandbox=None, timeout=180):
            self.compiled.append(compiled_text)
            return {
                "text": "fake reply",
                "thread_id": "test-thread-id",
                "sandbox": "workspace-write",
                "approval_policy": "never",
                "thread_start_result": {},
            }

        def status(self):
            return {"running": True, "pid": 0, "backend": "fake"}

        def broadcast(self, event):
            self.broadcasts.append(event)

    def setUp(self):
        # Isolate from the operator's real pause flag. This suite boots a
        # real server, which reads the real flag, so a legitimately paused
        # Captain failed the tests. Operator state leaking into tests is a
        # defect in the tests, not in the pause.
        import os
        self._pause_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._pause_dir.cleanup)
        _previous = os.environ.get("MONAD_LIVE_CAPTAIN_STATE_DIR")
        os.environ["MONAD_LIVE_CAPTAIN_STATE_DIR"] = self._pause_dir.name
        self.addCleanup(
            lambda: os.environ.__setitem__("MONAD_LIVE_CAPTAIN_STATE_DIR", _previous)
            if _previous is not None
            else os.environ.pop("MONAD_LIVE_CAPTAIN_STATE_DIR", None))

        import threading
        from http.server import ThreadingHTTPServer

        self.auth = AuthConfig(
            salt=b"0" * 16,
            password_hash=hashlib.scrypt(b"unused", salt=b"0" * 16, n=2**14, r=8, p=1, dklen=32),
            session_secret=b"1" * 32,
        )
        self._tmpdir = tempfile.TemporaryDirectory()
        self.store = LiveCaptainStore(Path(self._tmpdir.name) / "test.db")
        self.objectives = ObjectiveStore(Path(self._tmpdir.name) / "objectives.db")

        self.daemon = self._FakeDaemon()
        LiveCaptainHandler.daemon = self.daemon
        LiveCaptainHandler.store = self.store
        LiveCaptainHandler.auth = self.auth
        LiveCaptainHandler.objectives = self.objectives
        LiveCaptainHandler.arbiter = TurnArbiter()
        LiveCaptainHandler.speech_renderer = lambda text: {
            "audio_url": "/voice-api/artifacts/test.wav", "transcript": text,
        }
        for name, value in load_context_sources().items():
            setattr(LiveCaptainHandler, name, value)

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), LiveCaptainHandler)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=5)
        self.objectives.close()
        self._tmpdir.cleanup()

    def _url(self, path):
        return f"http://127.0.0.1:{self.port}{path}"

    def test_status_over_real_socket_requires_authentication(self):
        import urllib.error
        import urllib.request

        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(urllib.request.Request(self._url("/api/status")), timeout=5)
        self.assertEqual(ctx.exception.code, 401)

    def test_status_over_real_socket_with_valid_session(self):
        import urllib.request

        cookie = self.auth.issue_session()
        request = urllib.request.Request(
            self._url("/api/status"), headers={"Cookie": f"{COOKIE_NAME}={cookie}"}
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            self.assertEqual(response.status, 200)
            body = json.loads(response.read())
        self.assertIn("kernel_digest", body)
        self.assertIn("bearing_digest", body)
        self.assertIn("ledger_digest", body)
        self.assertEqual(body["session_id"], self.store.session_id)

    def test_turn_over_real_socket_persists_and_returns_reply(self):
        import urllib.request

        cookie = self.auth.issue_session()
        payload = json.dumps({"text": "end-to-end boot test message"}).encode("utf-8")
        request = urllib.request.Request(
            self._url("/api/turn"),
            data=payload,
            method="POST",
            headers={"Cookie": f"{COOKIE_NAME}={cookie}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            self.assertEqual(response.status, 200)
            body = json.loads(response.read())
        self.assertEqual(body["text"], "fake reply")
        self.assertEqual(body["thread_id"], "test-thread-id")
        self.assertEqual(body["speech_artifact"]["audio_url"], "/voice-api/artifacts/test.wav")

        messages, _ = self.store.load_recent_messages(10)
        self.assertTrue(any(m["text"] == "end-to-end boot test message" for m in messages))

    def test_concurrent_turn_context_is_compiled_after_prior_reply(self):
        import threading
        import urllib.request

        cookie = self.auth.issue_session()
        errors = []
        def send(text):
            try:
                request = urllib.request.Request(
                    self._url("/api/turn"), data=json.dumps({"text": text}).encode(), method="POST",
                    headers={"Cookie": f"{COOKIE_NAME}={cookie}", "Content-Type": "application/json"},
                )
                with urllib.request.urlopen(request, timeout=5) as response: response.read()
            except Exception as exc: errors.append(exc)

        first = threading.Thread(target=send, args=("first queued utterance",))
        second = threading.Thread(target=send, args=("second queued utterance",))
        first.start(); time.sleep(.02); second.start(); first.join(5); second.join(5)
        self.assertEqual(errors, [])
        self.assertEqual(len(self.daemon.compiled), 2)
        self.assertIn("Admiral: first queued utterance", self.daemon.compiled[1])
        self.assertIn("Captain: fake reply", self.daemon.compiled[1])


if __name__ == "__main__":
    unittest.main()
