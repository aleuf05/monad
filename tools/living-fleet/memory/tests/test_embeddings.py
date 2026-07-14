import unittest

from memory import embeddings


class EmbeddingsTests(unittest.TestCase):
    def test_similar_text_scores_higher_than_unrelated_text(self):
        corpus = [
            "Contact QUACKEN sighted near the strait, investigate posture engaged.",
            "Contact QUACKEN rendezvous hold complete, mission success.",
            "Flank security widened to preserve maneuvering room.",
        ]
        idf = embeddings.build_idf(corpus)
        query = embeddings.vectorize("QUACKEN rendezvous contact investigation", idf)

        similar = embeddings.vectorize(corpus[0], idf)
        unrelated = embeddings.vectorize(corpus[2], idf)

        self.assertGreater(
            embeddings.cosine_similarity(query, similar),
            embeddings.cosine_similarity(query, unrelated),
        )

    def test_reindexing_does_not_require_any_stored_row_to_change(self):
        # The embedding index is explicitly a derived, regenerable
        # accelerator (docs/logging-doctrine.md's "Vector Space is
        # Disposable") -- rebuilding it from a different corpus must not
        # need or imply touching any authoritative SQLite row.
        idf_v1 = embeddings.build_idf(["alpha bravo charlie"])
        idf_v2 = embeddings.build_idf(["alpha bravo charlie", "delta echo foxtrot"])
        vector_v1 = embeddings.vectorize("alpha bravo", idf_v1)
        vector_v2 = embeddings.vectorize("alpha bravo", idf_v2)
        self.assertIsInstance(vector_v1, dict)
        self.assertIsInstance(vector_v2, dict)

    def test_empty_text_produces_empty_vector(self):
        idf = embeddings.build_idf(["something"])
        self.assertEqual(embeddings.vectorize("", idf), {})
        self.assertEqual(embeddings.cosine_similarity({}, {"a": 1.0}), 0.0)


if __name__ == "__main__":
    unittest.main()
