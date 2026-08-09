import tempfile
import unittest
from pathlib import Path

from concept_retrieval import ConceptEngine, normalized_concept_title, spoken_brief
from persistence import LiveCaptainStore


class _Corpus:
    entries = []

    @classmethod
    def collect(cls, _root):
        return cls.entries


def _entry(path="docs/research/alpha.md", content="# Alpha\n\nCaptain concept evidence."):
    return {
        "id": "research/alpha", "path": path, "title": "Alpha", "category": "research",
        "status": "proposal", "mtime": 1.0, "content": content,
    }


class ConceptEngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        _Corpus.entries = [_entry()]
        self.engine = ConceptEngine(Path(self.tmp.name) / "concept.db", Path(self.tmp.name), _Corpus)
        self.addCleanup(self.engine.close)

    def test_sync_search_refresh_and_removal(self):
        first = self.engine.retrieve("Captain evidence")
        self.assertEqual(first["index"]["documents"], 1)
        self.assertEqual(first["evidence"][0]["heading"], "Alpha")

        _Corpus.entries = [_entry(content="# Alpha\n\nRevised kraken evidence.")]
        revised = self.engine.retrieve("kraken")
        self.assertEqual(revised["index"]["changed"], 1)
        self.assertIn("Revised kraken", revised["evidence"][0]["excerpt"])

        _Corpus.entries = []
        removed = self.engine.retrieve("kraken")
        self.assertEqual(removed["index"]["removed"], 1)
        self.assertEqual(removed["evidence"], [])

    def test_modes_and_spoken_contract(self):
        self.assertEqual(self.engine.classify("trace the history of Captain"), "history")
        self.assertEqual(self.engine.classify("where do these disagree?"), "conflict")
        answer = "SPOKEN BRIEF\nCourse held, Admiral.\n\nDEEPER CHART\nEvidence follows."
        self.assertEqual(spoken_brief(answer), "Course held, Admiral.")
        self.assertEqual(normalized_concept_title("Explain Live Captain?"), "Live Captain")


class ConceptPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "live.db"
        self.store = LiveCaptainStore(self.path)
        self.addCleanup(self.store.close)

    def test_rooms_are_isolated_and_revisions_append(self):
        first = self.store.create_concept_room("First")
        second = self.store.create_concept_room("Second")
        admiral = self.store.record_concept_turn(first["id"], "admiral", "Explain Alpha")
        captain = self.store.record_concept_turn(first["id"], "captain", "Alpha [S1]")
        evidence = [{"id": "S1", "path": "docs/a.md", "heading": "Alpha", "content_hash": "abc", "excerpt": "source"}]
        one = self.store.append_concept_revision(first["id"], "Alpha", "first", captain["id"], evidence)
        two = self.store.append_concept_revision(first["id"], "Alpha", "second", captain["id"], evidence)

        self.assertEqual(admiral["room_id"], first["id"])
        self.assertEqual(self.store.load_concept_turns(second["id"]), [])
        self.assertEqual(two["current_revision"], 2)
        self.assertEqual([item["synopsis"] for item in two["revisions"]], ["first", "second"])
        self.assertEqual(one["id"], two["id"])

    def test_rooms_survive_store_restart(self):
        room = self.store.create_concept_room("Persistent")
        self.store.close()
        self._cleanups.pop()  # avoid closing the already closed first store
        reopened = LiveCaptainStore(self.path)
        self.addCleanup(reopened.close)
        self.assertEqual(reopened.get_concept_room(room["id"])["title"], "Persistent")


if __name__ == "__main__":
    unittest.main()
