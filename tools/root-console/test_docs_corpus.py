import tempfile
import unittest
from pathlib import Path

import docs_corpus


class DocumentCorpusStatusTests(unittest.TestCase):
    def test_bold_staged_not_filed_header_is_staged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            incoming = root / "docs" / "incoming"
            incoming.mkdir(parents=True)
            (incoming / "packet.md").write_text(
                "# Packet\n\n**Status:** **Staged, not filed.** Captured verbatim.\n",
                encoding="utf-8",
            )
            entries = docs_corpus.collect(root)
        self.assertEqual(entries[0]["status"], docs_corpus.STATUS_STAGED)


if __name__ == "__main__":
    unittest.main()
