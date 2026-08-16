"""Runtime Operator Manual Indexer and Retrieval Subsystem.

Implements Addendum A5: Grounded runtime consultation of the canonical
Operator Manual (docs/manuals/LIVE_CAPTAIN_OPERATOR_MANUAL.md) without bloating every prompt.
"""

from __future__ import annotations

import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional

ROOT_DIR = Path(__file__).resolve().parent
REPO_ROOT = ROOT_DIR.parent.parent
DEFAULT_MANUAL_PATH = REPO_ROOT / "docs" / "manuals" / "LIVE_CAPTAIN_OPERATOR_MANUAL.md"


class OperatorManualReader:
    """Parses and retrieves relevant sections from the canonical Operator Manual."""

    def __init__(self, manual_path: Path = DEFAULT_MANUAL_PATH):
        self.manual_path = manual_path
        self._sections: List[Dict[str, str]] = []
        self._last_mtime: float = 0.0
        self._load_and_index()

    def _load_and_index(self) -> None:
        if not self.manual_path.exists():
            self._sections = []
            return

        mtime = self.manual_path.stat().st_mtime
        if mtime == self._last_mtime and self._sections:
            return

        self._last_mtime = mtime
        content = self.manual_path.read_text(encoding="utf-8", errors="replace")
        
        # Split by markdown H2 (## ) headers
        chunks = re.split(r'\n(?=##\s+)', content)
        sections = []
        for chunk in chunks:
            lines = chunk.strip().split('\n')
            if not lines:
                continue
            header = lines[0].lstrip('#').strip()
            body = '\n'.join(lines[1:]).strip()
            sections.append({
                "header": header,
                "body": body,
                "full_text": chunk.strip()
            })
        self._sections = sections

    def query(self, query_text: str, max_sections: int = 2) -> Dict[str, Any]:
        """Finds the most relevant manual sections for a query."""
        self._load_and_index()
        if not self._sections:
            return {
                "found": False,
                "query": query_text,
                "sections": [],
                "source": str(self.manual_path),
                "summary": "Operator Manual not found on host."
            }

        q_terms = [t.lower() for t in re.findall(r'\w+', query_text) if len(t) > 2]
        scored_sections = []

        for sec in self._sections:
            score = 0
            header_lower = sec["header"].lower()
            body_lower = sec["body"].lower()

            for term in q_terms:
                if term in header_lower:
                    score += 5
                if term in body_lower:
                    score += 1

            if score > 0:
                scored_sections.append((score, sec))

        scored_sections.sort(key=lambda x: x[0], reverse=True)
        top_matches = [s[1] for s in scored_sections[:max_sections]]

        if not top_matches:
            # Return top overview section if no specific match
            top_matches = self._sections[:1]

        summary_parts = []
        for match in top_matches:
            summary_parts.append(f"### Section: {match['header']}\n{match['body'][:1500]}")

        return {
            "found": True,
            "query": query_text,
            "sections": top_matches,
            "source": str(self.manual_path),
            "summary": "\n\n".join(summary_parts)
        }


MANUAL_READER = OperatorManualReader()
