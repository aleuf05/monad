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
import subprocess
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from context_compiler import (
    ContextCompilerError,
    compile_live_captain_context,
    context_size_metrics,
    format_chronological_messages,
    load_required_text,
)
from persistence import LiveCaptainStore, PersistenceError
from run_tests import append_report, build_report
from server import browser_sse_payload, load_context_sources
import generated_images
from context_metabolism import (
    ContinuityFact,
    PromotionPolicy,
    assess_candidate,
    audit_ledger,
    consolidate,
    contradictions,
    retire,
    retrieve,
    promotion_decision,
    ingest_attested_candidate,
)


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
                "schema": "live-captain-candidate/v1",
                "key": "conference.token",
                "value": "Conference",
                "evidence_ref": "command:157",
                "evidence_sha256": digest,
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
                "schema": "live-captain-candidate/v1",
                "key": "conference.token",
                "value": "Conference",
                "evidence_ref": "command:157",
                "evidence_sha256": "0" * 64,
            }
        )
        with self.assertRaisesRegex(ValueError, "independently available"):
            ingest_attested_candidate(payload, {})
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            ingest_attested_candidate(payload, {"command:157": evidence})

    def test_candidate_ingestion_rejects_schema_drift(self):
        payload = json.dumps(
            {
                "schema": "live-captain-candidate/v1",
                "key": "conference.token",
                "value": "Conference",
                "evidence_ref": "command:157",
                "evidence_sha256": "0" * 64,
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
                    "schema": "live-captain-candidate/v1",
                    "key": "conference.token",
                    "value": "Conference",
                    "evidence_ref": evidence_ref,
                    "evidence_sha256": hashlib.sha256(evidence).hexdigest(),
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

    def test_captain_message_cannot_attest_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = LiveCaptainStore(Path(tmp) / "test.db")
            seq = store.record_message("captain", "Conference", "kd", "bd", "ld")
            with self.assertRaisesRegex(PersistenceError, "only persisted Admiral"):
                store.load_admiral_attestation(seq)


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


if __name__ == "__main__":
    unittest.main()
