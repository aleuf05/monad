#!/usr/bin/env python3
"""Rust core vs Python reference — same input, same answer.

A rewrite in a second language is only safe if something holds the two to
each other. These tests are that something. They skip rather than fail when
the core is not built, so a checkout without a Rust toolchain still runs
green on the Python path.
"""

from __future__ import annotations

import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "aegis-inspect"))
import inspector  # noqa: E402
import solver  # noqa: E402
from test_solver import build_glb, tetra  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
GASKET = REPO_ROOT / "web/assets/models/gasket/gasket.glb"


def as_f32(points):
    """glTF stores positions as f32 and the core pipe carries them as f32, so
    a synthetic mesh built from Python f64 literals would hand the two engines
    subtly different numbers and fail parity for a reason that never occurs on
    a real asset. Quantise first, compare after."""
    quantise = struct.Struct("<3f")
    return [quantise.unpack(quantise.pack(*p)) for p in points]


def fragmented_mesh(shells: int = 40, spacing: float = 0.05):
    points, faces = [], []
    for n in range(shells):
        p, f = tetra((n * spacing, (n % 3) * 0.01, 0.0), spacing * 0.3)
        base = len(points)
        points += p
        faces += [(i + base, j + base, k + base) for i, j, k in f]
    return as_f32(points), faces


@unittest.skipUnless(solver.core_available(), "rigging core not built")
class ParityTests(unittest.TestCase):
    def _both(self, points, faces, joint_count=5):
        indices = [v for f in faces for v in f]
        rust = solver.solve_core(points, indices, joint_count, engine="rust")
        python = solver.solve_core(points, indices, joint_count, engine="python")
        self.assertEqual(rust[2], "rust")
        self.assertEqual(python[2], "python")
        return rust, python

    def test_skeletons_agree(self):
        points, faces = fragmented_mesh()
        (rs, _, _), (ps, _, _) = self._both(points, faces)
        self.assertEqual(rs["axis"], ps["axis"])
        self.assertAlmostEqual(rs["bone_span"], ps["bone_span"], places=9)
        self.assertEqual(len(rs["joints"]), len(ps["joints"]))
        for a, b in zip(rs["joints"], ps["joints"]):
            for x, y in zip(a, b):
                self.assertAlmostEqual(x, y, places=6)

    def test_shell_counts_agree(self):
        points, faces = fragmented_mesh()
        (_, rk, _), (_, pk, _) = self._both(points, faces)
        self.assertEqual(rk["shells"], pk["shells"])
        self.assertEqual(rk["rigid_shells"], pk["rigid_shells"])
        self.assertEqual(rk["blended_shells"], pk["blended_shells"])
        self.assertEqual(rk["rigid_vertices"], pk["rigid_vertices"])
        self.assertEqual(rk["blended_vertices"], pk["blended_vertices"])

    def test_every_weight_agrees(self):
        points, faces = fragmented_mesh(shells=25, spacing=0.09)
        (_, rk, _), (_, pk, _) = self._both(points, faces, joint_count=7)
        self.assertEqual(list(rk["joint_ids"]), list(pk["joint_ids"]))
        for a, b in zip(rk["weights"], pk["weights"]):
            self.assertAlmostEqual(a, b, places=6)

    def test_agreement_holds_on_a_blended_mesh(self):
        """Force blending: one long shell that straddles every joint."""
        points = as_f32([(x * 0.01, 0.0, 0.0) for x in range(300)])
        faces = [(i, i + 1, i + 2) for i in range(298)]
        (_, rk, _), (_, pk, _) = self._both(points, faces, joint_count=6)
        self.assertGreater(rk["blended_shells"], 0)
        self.assertEqual(list(rk["joint_ids"]), list(pk["joint_ids"]))
        for a, b in zip(rk["weights"], pk["weights"]):
            self.assertAlmostEqual(a, b, places=6)

    @unittest.skipUnless(GASKET.is_file(), "gasket.glb not present")
    def test_agreement_on_the_real_corpus(self):
        """Synthetic parity is easy. This one runs both engines over an actual
        asset — 29,378 vertices, 395 shells, Tripo-generated."""
        gltf, blob, _ = solver._split_glb(GASKET.read_bytes())
        prim = gltf["meshes"][0]["primitives"][0]
        positions = solver._read_positions(gltf, blob, prim["attributes"]["POSITION"])
        indices = inspector._read_indices(gltf, blob, 0, prim["indices"])

        _, rk, _ = solver.solve_core(positions, indices, 8, engine="rust")
        _, pk, _ = solver.solve_core(positions, indices, 8, engine="python")
        self.assertEqual(rk["shells"], pk["shells"])
        self.assertEqual(rk["rigid_shells"], pk["rigid_shells"])
        self.assertEqual(list(rk["joint_ids"]), list(pk["joint_ids"]))
        for a, b in zip(rk["weights"], pk["weights"]):
            self.assertAlmostEqual(a, b, places=6)

    def test_both_engines_write_the_same_file(self):
        import tempfile

        points, faces = fragmented_mesh(shells=12, spacing=0.08)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "s.glb"
            source.write_bytes(build_glb(points, faces))
            a = solver.write_rigged(source, root / "rust.glb", 5, engine="rust")
            b = solver.write_rigged(source, root / "python.glb", 5, engine="python")
            self.assertEqual(a["rigged_sha256"], b["rigged_sha256"])
            self.assertEqual(a["engine"], "rust")
            self.assertEqual(b["engine"], "python")


if __name__ == "__main__":
    unittest.main(verbosity=2)
