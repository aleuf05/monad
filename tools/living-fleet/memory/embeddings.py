"""Local, deterministic, stdlib-only retrieval accelerator.

docs/logging-doctrine.md ("Vector Space is Disposable") and the real
Helmsman V1 precedent (a vector DB wrongly used as *primary* memory storage)
rule out a vector database as the source of truth here, and this repo's
zero-third-party-dependency convention rules out an external embeddings
package or API (which would also mean secrets/network calls this
single-operator demo doesn't need). So "embeddings" in this module means a
plain bag-of-words TF-IDF vector, computed with nothing but `re`/`math`/
`collections`, fully regenerable from the SQLite rows at any time, and never
the sole signal in context.py's ranking.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Iterable

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall((text or "").lower())


def build_idf(corpus: Iterable[str]) -> dict[str, float]:
    """corpus: one string per document (e.g. one per episodic memory)."""
    documents = list(corpus)
    doc_count = max(1, len(documents))
    document_frequency: Counter[str] = Counter()
    for text in documents:
        for token in set(tokenize(text)):
            document_frequency[token] += 1
    return {
        token: math.log((doc_count + 1) / (freq + 1)) + 1.0
        for token, freq in document_frequency.items()
    }


def vectorize(text: str, idf: dict[str, float]) -> dict[str, float]:
    tokens = tokenize(text)
    if not tokens:
        return {}
    term_frequency = Counter(tokens)
    max_frequency = max(term_frequency.values())
    vector = {}
    for token, count in term_frequency.items():
        weight = idf.get(token, math.log(2.0))
        vector[token] = (count / max_frequency) * weight
    return vector


def cosine_similarity(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    shared = set(a) & set(b)
    if not shared:
        return 0.0
    numerator = sum(a[token] * b[token] for token in shared)
    norm_a = math.sqrt(sum(value * value for value in a.values()))
    norm_b = math.sqrt(sum(value * value for value in b.values()))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return numerator / (norm_a * norm_b)
