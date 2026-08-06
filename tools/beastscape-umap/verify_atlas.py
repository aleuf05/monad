#!/usr/bin/env python3
"""Verify the exported atlas is fixed, diverse, and exactly navigable."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
ATLAS = ROOT / "web/toys/beastscape/umap-atlas.v1.json"


def main() -> None:
    payload = json.loads(ATLAS.read_text())
    assert payload["schema"] == "monad.beastscapeFoundry.v0.1"
    assert len(payload["spaces"]) == 3
    results = []
    for space in payload["spaces"]:
        specimens = space["specimens"]
        chart = np.asarray([item["chart"] for item in specimens])
        genotypes = np.asarray([item["v"] for item in specimens])
        descriptors = np.asarray([item["descriptor"] for item in specimens])
        assert chart.shape == (720, 3)
        assert genotypes.shape == (720, 3)
        assert descriptors.shape == (720, 24)
        assert np.isfinite(chart).all() and np.isfinite(genotypes).all()
        assert len({item["atlasId"] for item in specimens}) == 720
        assert len({item["region"] for item in specimens}) == 6
        assert np.all((chart >= 0) & (chart <= 1))
        probes = np.arange(0, len(specimens), 37)
        recovered = []
        for probe in probes:
            distances = np.sum((chart - chart[probe]) ** 2, axis=1)
            recovered.append(int(np.argmin(distances)) == int(probe))
        assert all(recovered)

        def decode(coordinate: np.ndarray) -> np.ndarray:
            distances = np.sum((chart - coordinate) ** 2, axis=1)
            nearest = np.argsort(distances)[:12]
            bandwidth = max(float(distances[nearest[-1]]) * 0.45, 0.00008)
            weights = np.exp(-distances[nearest] / bandwidth)
            weights /= weights.sum()
            return weights @ descriptors[nearest]

        origin = chart[417] + np.asarray([0.003, -0.002, 0.001])
        epsilon = np.asarray([1e-6, 0.0, 0.0])
        phenotype_delta = float(np.linalg.norm(decode(origin + epsilon) - decode(origin)))
        assert 0 < phenotype_delta < 0.01
        results.append({
            "id": space["id"],
            "specimens": len(specimens),
            "exact_navigation_probes": len(probes),
            "microstep_phenotype_delta": phenotype_delta,
        })

    print(
        json.dumps(
            {
                "status": "ready",
                "candidate_beastscapes": len(results),
                "results": results,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
