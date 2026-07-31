#!/usr/bin/env python3
"""Fast proof that the local Beastscape UMAP stack can fit and navigate."""

from __future__ import annotations

import json

import numpy as np
import umap
from sklearn.datasets import make_blobs
from sklearn.manifold import trustworthiness


def main() -> None:
    descriptors, _ = make_blobs(
        n_samples=360,
        n_features=24,
        centers=9,
        cluster_std=1.15,
        random_state=1701,
    )
    descriptors = descriptors.astype(np.float32)

    mapper = umap.UMAP(
        n_components=3,
        n_neighbors=18,
        min_dist=0.12,
        metric="euclidean",
        init="random",
        random_state=1701,
        transform_seed=1701,
        n_jobs=1,
    )
    chart = mapper.fit_transform(descriptors)
    probe = mapper.transform(descriptors[:12] + np.float32(0.01))

    assert chart.shape == (360, 3)
    assert probe.shape == (12, 3)
    assert np.isfinite(chart).all()
    assert np.isfinite(probe).all()

    local_fidelity = float(
        trustworthiness(descriptors, chart, n_neighbors=10)
    )
    assert local_fidelity >= 0.90, local_fidelity

    print(
        json.dumps(
            {
                "status": "ready",
                "umap_version": umap.__version__,
                "atlas_descriptors": list(descriptors.shape),
                "chart_coordinates": list(chart.shape),
                "out_of_sample_probe": list(probe.shape),
                "trustworthiness_at_10": round(local_fidelity, 4),
                "finite": True,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
