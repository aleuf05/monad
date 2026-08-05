#!/usr/bin/env python3
"""Tests for the Aegis rigging solver.

The load-bearing one is `test_disjoint_shells_never_share_influence`. Every
other test here checks that the solver does something sensible; that one
checks the thing Packet Beta actually warned about.
"""

from __future__ import annotations

import json
import struct
import sys
import tempfile
import unittest
from array import array
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "aegis-inspect"))
import inspector  # noqa: E402
import solver  # noqa: E402


def tetra(origin, size=0.1):
    """Four vertices, four faces — the smallest thing that is a closed shell."""
    ox, oy, oz = origin
    points = [(ox, oy, oz), (ox + size, oy, oz),
              (ox, oy + size, oz), (ox, oy, oz + size)]
    faces = [(0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 3)]
    return points, faces


def build_glb(points, faces) -> bytes:
    """A minimal single-primitive GLB, so the round-trip test exercises the
    real writer instead of a mock."""
    pos = array("f")
    for p in points:
        pos.extend(p)
    idx = array("I")
    for f in faces:
        idx.extend(f)

    pos_bytes, idx_bytes = pos.tobytes(), idx.tobytes()
    blob = pos_bytes + idx_bytes
    gltf = {
        "asset": {"version": "2.0", "generator": "test"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0}],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0}, "indices": 1}]}],
        "accessors": [
            {"bufferView": 0, "componentType": 5126, "count": len(points),
             "type": "VEC3"},
            {"bufferView": 1, "componentType": 5125, "count": len(idx),
             "type": "SCALAR"},
        ],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": len(pos_bytes)},
            {"buffer": 0, "byteOffset": len(pos_bytes), "byteLength": len(idx_bytes)},
        ],
        "buffers": [{"byteLength": len(blob)}],
    }
    json_chunk = json.dumps(gltf).encode()
    json_chunk += b" " * (-len(json_chunk) % 4)
    bin_chunk = blob + b"\x00" * (-len(blob) % 4)
    total = 12 + 8 + len(json_chunk) + 8 + len(bin_chunk)
    out = b"glTF" + struct.pack("<II", 2, total)
    out += struct.pack("<II", len(json_chunk), solver.CHUNK_JSON) + json_chunk
    out += struct.pack("<II", len(bin_chunk), solver.CHUNK_BIN) + bin_chunk
    return out


class SkeletonTests(unittest.TestCase):
    def test_picks_the_dominant_axis(self):
        points = [(x * 0.1, 0.0, 0.0) for x in range(20)] + [(0.0, 0.2, 0.05)]
        skeleton = solver.solve_skeleton(points, 4)
        self.assertEqual(skeleton["axis_name"], "X")

    def test_picks_y_when_y_is_longest(self):
        points = [(0.0, y * 0.1, 0.0) for y in range(20)] + [(0.2, 0.0, 0.05)]
        self.assertEqual(solver.solve_skeleton(points, 4)["axis_name"], "Y")

    def test_joints_are_ordered_along_the_axis(self):
        points = [(x * 0.05, 0.0, 0.0) for x in range(40)]
        skeleton = solver.solve_skeleton(points, 6)
        coords = [j[skeleton["axis"]] for j in skeleton["joints"]]
        self.assertEqual(coords, sorted(coords))
        self.assertEqual(len(skeleton["joints"]), 6)

    def test_chain_is_parented_root_to_tip(self):
        points = [(x * 0.05, 0.0, 0.0) for x in range(40)]
        skeleton = solver.solve_skeleton(points, 5)
        self.assertEqual(skeleton["parents"], [-1, 0, 1, 2, 3])
        self.assertEqual(skeleton["names"][0], "@Root")
        self.assertEqual(skeleton["names"][-1], "@Tip")

    def test_rejects_a_single_joint(self):
        with self.assertRaises(solver.RigError):
            solver.solve_skeleton([(0, 0, 0), (1, 0, 0)], 1)

    def test_rejects_degenerate_geometry(self):
        with self.assertRaises(solver.RigError):
            solver.solve_skeleton([(0, 0, 0)] * 5, 3)

    def test_verify_acyclic(self):
        self.assertTrue(solver.verify_acyclic([-1, 0, 1, 2]))
        self.assertFalse(solver.verify_acyclic([1, 0]))
        self.assertFalse(solver.verify_acyclic([-1, 2, 1]))

    def test_chain_follows_mass_off_axis(self):
        """A bent bar should give joints at different heights, not a
        straight centreline."""
        points = [(x * 0.05, (x * 0.05) ** 2, 0.0) for x in range(21)]
        skeleton = solver.solve_skeleton(points, 5)
        heights = [j[1] for j in skeleton["joints"]]
        self.assertGreater(heights[-1], heights[0] + 0.1)


class SkinningTests(unittest.TestCase):
    def _weights_for(self, points, labels, joint_count=5):
        skeleton = solver.solve_skeleton(points, joint_count)
        return skeleton, solver.solve_weights(points, labels, skeleton)

    def test_compact_shell_is_bound_rigidly(self):
        points = [(x * 0.05, 0.0, 0.0) for x in range(21)]
        labels = [0 if p[0] < 0.15 else 1 for p in points]
        _, skin = self._weights_for(points, labels)
        self.assertEqual(skin["rigid_shells"], 1)

    def test_spanning_shell_is_blended(self):
        points = [(x * 0.05, 0.0, 0.0) for x in range(21)]
        labels = [0] * len(points)
        _, skin = self._weights_for(points, labels)
        self.assertEqual(skin["blended_shells"], 1)
        self.assertEqual(skin["rigid_shells"], 0)

    def test_weights_always_sum_to_one(self):
        points = [(x * 0.05, (x % 3) * 0.01, 0.0) for x in range(60)]
        labels = [i // 7 for i in range(60)]
        _, skin = self._weights_for(points, labels)
        self.assertTrue(skin["weights_sum_to_one"])
        self.assertEqual(skin["unweighted_vertices"], 0)
        self.assertLessEqual(skin["max_weight_error"], solver.WEIGHT_EPSILON)

    def test_disjoint_shells_never_share_influence(self):
        """The bleed test. Two small clusters sitting either side of a joint
        boundary must come out bound to one bone each, with no vertex holding
        partial influence from a bone belonging to the other cluster's
        neighbourhood. This is the failure Packet Beta named."""
        left = [(0.02 + i * 0.001, 0.0, 0.0) for i in range(10)]
        right = [(0.98 - i * 0.001, 0.0, 0.0) for i in range(10)]
        points = left + right
        labels = [0] * 10 + [1] * 10
        _, skin = self._weights_for(points, labels)

        self.assertEqual(skin["rigid_shells"], 2)
        self.assertEqual(skin["blended_shells"], 0)

        weights, ids = skin["weights"], skin["joint_ids"]
        for v in range(len(points)):
            influences = [(ids[4 * v + k], weights[4 * v + k])
                          for k in range(4) if weights[4 * v + k] > 0]
            self.assertEqual(len(influences), 1, f"vertex {v} has split influence")
            self.assertEqual(influences[0][1], 1.0)

        left_joint = ids[0]
        right_joint = ids[4 * 10]
        self.assertNotEqual(left_joint, right_joint)

    def test_denser_bones_convert_rigid_shells_to_blended(self):
        """Bone density is the knob that decides how much of the mesh can
        deform at all — below the fragmentation scale nothing blends."""
        points = [(x * 0.01, 0.0, 0.0) for x in range(101)]
        labels = [i // 25 for i in range(101)]
        _, sparse = self._weights_for(points, labels, joint_count=3)
        _, dense = self._weights_for(points, labels, joint_count=20)
        self.assertGreater(dense["blended_shells"], sparse["blended_shells"])


class ShellTests(unittest.TestCase):
    def test_two_tetrahedra_are_two_shells(self):
        pa, fa = tetra((0, 0, 0))
        pb, fb = tetra((1, 0, 0))
        faces = fa + [(i + 4, j + 4, k + 4) for i, j, k in fb]
        indices = [v for f in faces for v in f]
        labels = inspector.connected_components(indices, 8)
        self.assertEqual(len(set(labels)), 2)
        self.assertEqual(len(set(labels[:4])), 1)
        self.assertEqual(len(set(labels[4:])), 1)


class WriterTests(unittest.TestCase):
    def test_round_trip_produces_a_rigged_asset(self):
        points, faces = [], []
        for n in range(6):
            p, f = tetra((n * 0.2, 0.0, 0.0), 0.05)
            base = len(points)
            points += p
            faces += [(i + base, j + base, k + base) for i, j, k in f]

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "static.glb"
            dest = root / "rigged.glb"
            source.write_bytes(build_glb(points, faces))

            before = inspector.describe(source, root)
            self.assertEqual(before["state"], "static")

            report = solver.write_rigged(source, dest, 4)
            self.assertTrue(report["weights_sum_to_one"])
            self.assertEqual(report["shells"], 6)

            after = inspector.describe(dest, root)
            self.assertEqual(after["state"], "rigged")
            self.assertEqual(after["skins"], 1)
            self.assertEqual(after["joints"], 4)
            self.assertTrue(after["has_weights"])
            self.assertEqual(after["vertices"], before["vertices"])
            self.assertEqual(after["triangles"], before["triangles"])

    def test_original_geometry_is_untouched(self):
        """Appending to the buffer must not move anything that was there."""
        points, faces = [], []
        for n in range(4):
            p, f = tetra((n * 0.3, 0.0, 0.0), 0.05)
            base = len(points)
            points += p
            faces += [(i + base, j + base, k + base) for i, j, k in f]

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, dest = root / "s.glb", root / "d.glb"
            source.write_bytes(build_glb(points, faces))
            solver.write_rigged(source, dest, 3)

            gltf_a, blob_a, _ = solver._split_glb(source.read_bytes())
            gltf_b, blob_b, _ = solver._split_glb(dest.read_bytes())
            pos_a = solver._read_positions(gltf_a, blob_a, 0)
            pos_b = solver._read_positions(gltf_b, blob_b, 0)
            self.assertEqual(pos_a, pos_b)

    def test_refuses_a_file_that_is_not_a_glb(self):
        with tempfile.TemporaryDirectory() as tmp:
            bogus = Path(tmp) / "x.glb"
            bogus.write_bytes(b"not a gltf file at all")
            with self.assertRaises(solver.RigError):
                solver.write_rigged(bogus, Path(tmp) / "out.glb")


if __name__ == "__main__":
    unittest.main(verbosity=2)
