#!/usr/bin/env python3
"""Build the first fixed Beastscape atlas and its learned UMAP chart."""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import umap
from sklearn.preprocessing import StandardScaler

TAU = math.tau
REGIONS = ("radial", "bilateral", "segmented", "colonial", "annular", "arborescent")
ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "web/toys/beastscape/umap-atlas.v1.json"
SPACES = (
    {
        "id": "open-ocean",
        "name": "Open Ocean",
        "hypothesis": "A balanced mixed grammar produces broad topology coverage but weak structural identity.",
        "operations": ["seed", "differentiate", "branch", "repeat", "fuse", "terminate"],
        "bias": [0, 0, 0, 0, 0, 0],
    },
    {
        "id": "metameric-forge",
        "name": "Metameric Forge",
        "hypothesis": "Repetition before differentiation produces coherent axial, segmented and branching organisms.",
        "operations": ["seed", "repeat", "segment", "differentiate", "branch", "terminate"],
        "bias": [-0.12, 0.18, 0.22, -0.10, -0.08, 0.16],
    },
    {
        "id": "symbiotic-reef",
        "name": "Symbiotic Reef",
        "hypothesis": "Budding and fusion before termination produces multicore colonies, rings and membrane systems.",
        "operations": ["seed", "bud", "fuse", "differentiate", "membrane", "terminate"],
        "bias": [0.10, -0.12, -0.12, 0.22, 0.18, -0.06],
    },
)


def fract(value: float) -> float:
    return value - math.floor(value)


def describe(v: np.ndarray) -> tuple[list[float], int]:
    a, b, c = (float(x) for x in v)
    centers = 1 + math.floor(fract(a * 7 + b * 11 + c * 13) * 5)
    symmetry = 3 + math.floor(fract(a * 17 + b * 5 + c * 3) * 9)
    depth = 1 + math.floor(fract(a * 5 + b * 19 + c * 7) * 4)
    branch = fract(a * 13 + b * 23 + c * 29)
    fusion = fract(a * 31 + b * 7 + c * 17)
    segments = 3 + math.floor(fract(a * 37 + b * 13 + c * 5) * 10)
    curl = (fract(a * 11 + b * 41 + c * 19) - 0.5) * 1.8
    spread = 0.45 + fract(a * 3 + b * 17 + c * 43) * 0.55
    membrane = fract(a * 47 + b * 2 + c * 23)
    breakage = fract(a * 29 + b * 31 + c * 7)
    scores = [
        0.5 + 0.5 * math.sin(TAU * (a * (i + 2) + b * (i * 3 + 1) + c * (i * 5 + 2)))
        for i in range(6)
    ]
    regime = int(np.argmax(scores))
    ranked = sorted(scores, reverse=True)
    boundary = max(0.0, min(1.0, 1 - (ranked[0] - ranked[1]) * 6))

    # Structural phenotype vector: generative parameters, regime affinities,
    # and nonlinear interactions. Raw navigation coordinates are excluded.
    descriptor = [
        centers, symmetry, depth, branch, fusion, segments, curl, spread,
        membrane, breakage, boundary, *scores,
        branch * depth, fusion * centers, membrane * segments,
        abs(curl) * symmetry, spread * depth, branch * (1 - fusion),
        membrane * fusion,
    ]
    return descriptor, regime


def specialize(descriptor: list[float], space: dict) -> tuple[list[float], int]:
    values = descriptor.copy()
    if space["id"] == "metameric-forge":
        values[2] = min(4, values[2] + 1)
        values[3] = min(1, 0.25 + values[3] * 0.75)
        values[5] = min(12, values[5] + 2)
        values[7] = min(1, values[7] * 1.08)
    elif space["id"] == "symbiotic-reef":
        values[0] = min(5, values[0] + 1)
        values[4] = min(1, 0.30 + values[4] * 0.70)
        values[8] = min(1, 0.35 + values[8] * 0.65)
        values[3] *= 0.78
    scores = [max(0.0, min(1.0, score + bias)) for score, bias in zip(values[11:17], space["bias"])]
    values[11:17] = scores
    ranked = sorted(scores, reverse=True)
    values[10] = max(0.0, min(1.0, 1 - (ranked[0] - ranked[1]) * 6))
    values[17:] = [
        values[3] * values[2],
        values[4] * values[0],
        values[8] * values[5],
        abs(values[6]) * values[1],
        values[7] * values[2],
        values[3] * (1 - values[4]),
        values[8] * values[4],
    ]
    return values, int(np.argmax(scores))


def build_space(space: dict, seed: int) -> dict:
    rng = np.random.default_rng(seed)
    samples = rng.random((720, 3), dtype=np.float32)
    described = [specialize(describe(v)[0], space) for v in samples]
    descriptors = np.asarray([item[0] for item in described], dtype=np.float32)
    scaled = StandardScaler().fit_transform(descriptors)
    mapper = umap.UMAP(
        n_components=3,
        n_neighbors=24,
        min_dist=0.08,
        metric="euclidean",
        init="random",
        random_state=seed,
        transform_seed=seed,
        n_jobs=1,
        n_epochs=250,
    )
    chart = mapper.fit_transform(scaled)
    low, high = chart.min(axis=0), chart.max(axis=0)
    chart = (chart - low) / np.maximum(high - low, 1e-9)
    specimens = []
    for index, (v, coordinate, (descriptor, regime)) in enumerate(zip(samples, chart, described)):
        specimens.append({
            "atlasId": f"{space['id']}-{index:04d}",
            "v": [round(float(x), 6) for x in v],
            "chart": [round(float(x), 6) for x in coordinate],
            "descriptor": [round(float(x), 6) for x in descriptor],
            "region": REGIONS[regime],
        })
    counts = {region: sum(item["region"] == region for item in specimens) for region in REGIONS}
    evidence = {
        "specimens": len(specimens),
        "topologies": sum(count > 0 for count in counts.values()),
        "regionDistribution": counts,
        "transitionDensity": round(float(np.mean(descriptors[:, 10] > 0.5)), 3),
        "descriptorDispersion": round(float(np.mean(np.std(scaled, axis=0))), 3),
        "validity": "generator-constrained",
    }
    return {**space, "seed": seed, "evidence": evidence, "specimens": specimens}


def main() -> None:
    spaces = [build_space(space, 20260729 + index * 101) for index, space in enumerate(SPACES)]
    payload = {
        "schema": "monad.beastscapeFoundry.v0.1",
        "method": "UMAP",
        "dimensions": {"descriptor": 24, "chart": 3},
        "defaultSpace": spaces[0]["id"],
        "spaces": spaces,
    }
    OUTPUT.write_text(json.dumps(payload, separators=(",", ":")) + "\n")
    print(json.dumps({
        "schema": payload["schema"],
        "method": payload["method"],
        "dimensions": payload["dimensions"],
        "spaces": [{"id": item["id"], **item["evidence"]} for item in spaces],
    }, indent=2))
    print(f"wrote {OUTPUT}")


if __name__ == "__main__":
    main()
