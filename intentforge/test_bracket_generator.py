import math
import unittest

from bracket_generator import DesignIntentViolation, generate_fan_mount_bracket
from demo_fan_bracket import build_demo_intent
from design_intent import EdgeNotch, Envelope, FanMountBracketIntent, Hole


class TestFanMountBracket(unittest.TestCase):
    def setUp(self):
        self.intent = build_demo_intent()
        self.mesh, self.status, self.warnings = generate_fan_mount_bracket(self.intent)

    def test_watertight(self):
        self.assertTrue(self.mesh.is_watertight())

    def test_volume_matches_independent_area_calculation(self):
        # Independently computed from the contract's own numbers (not
        # from the generator's internals) -- the plate area minus the
        # notch minus each hole's polygon-approximated circle area,
        # times thickness. This is the check that actually caught the
        # hole-wall winding bug during development.
        w, h = self.intent.envelope.width, self.intent.envelope.height
        notch_area = self.intent.cable_notch.width * self.intent.cable_notch.depth
        holes = list(self.intent.existing_holes)
        fx, fy = self.intent.fan_center
        half = self.intent.fan_bolt_spacing / 2
        for dx, dy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            holes.append(Hole(fx + dx * half, fy + dy * half, self.intent.fan_bolt_diameter, "fan bolt"))
        holes.append(Hole(fx, fy, self.intent.fan_airflow_diameter, "airflow"))

        # 24-gon polygon area, not true circle area, to match circle_points(n=24)
        def polygon_hole_area(diameter, n=24):
            r = diameter / 2
            return 0.5 * n * r * r * math.sin(2 * math.pi / n)

        net_area = w * h - notch_area - sum(polygon_hole_area(hh.diameter) for hh in holes)
        expected_volume = net_area * self.intent.envelope.thickness
        self.assertAlmostEqual(self.mesh.signed_volume(), expected_volume, delta=0.5)

    def test_hole_positions_present_in_mesh(self):
        # Every requested hole's ring must actually appear in the mesh
        # at the requested center and radius -- not just "some hole
        # somewhere." Checked by finding mesh vertices near each
        # expected radius from the expected center and confirming their
        # centroid recovers the requested center.
        fx, fy = self.intent.fan_center
        half = self.intent.fan_bolt_spacing / 2
        expected = list(self.intent.existing_holes)
        for dx, dy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            expected.append(Hole(fx + dx * half, fy + dy * half, self.intent.fan_bolt_diameter, "fan bolt"))
        expected.append(Hole(fx, fy, self.intent.fan_airflow_diameter, "airflow"))

        # Caps and walls each contribute their own vertex entries at the
        # same physical rim (see Mesh.is_watertight's docstring) --
        # dedupe by rounded coordinate before computing a ring centroid,
        # or a hole ring gets double-counted against itself.
        seen = set()
        top_verts = []
        for v in self.mesh.vertices:
            if abs(v[2] - self.intent.envelope.thickness / 2) >= 1e-6:
                continue
            key = (round(v[0], 6), round(v[1], 6))
            if key in seen:
                continue
            seen.add(key)
            top_verts.append(v)
        for hole in expected:
            r = hole.diameter / 2
            ring = [v for v in top_verts if abs(math.hypot(v[0] - hole.cx, v[1] - hole.cy) - r) < 0.05]
            self.assertGreater(
                len(ring), 8, f"expected a hole ring near ({hole.cx},{hole.cy}) r={r}, found {len(ring)} matching vertices"
            )
            cx = sum(v[0] for v in ring) / len(ring)
            cy = sum(v[1] for v in ring) / len(ring)
            self.assertAlmostEqual(cx, hole.cx, delta=0.1)
            self.assertAlmostEqual(cy, hole.cy, delta=0.1)

    def test_envelope_respected(self):
        (min_x, min_y, min_z), (max_x, max_y, max_z) = self.mesh.bounding_box()
        w, h, t = self.intent.envelope.width, self.intent.envelope.height, self.intent.envelope.thickness
        self.assertGreaterEqual(min_x, -w / 2 - 1e-6)
        self.assertLessEqual(max_x, w / 2 + 1e-6)
        self.assertGreaterEqual(min_y, -h / 2 - 1e-6)
        self.assertLessEqual(max_y, h / 2 + 1e-6)
        self.assertAlmostEqual(max_z - min_z, t, delta=1e-6)

    def test_overlapping_holes_rejected(self):
        bad = FanMountBracketIntent(
            purpose="deliberately invalid: overlapping holes",
            envelope=Envelope(width=70, height=70, thickness=3),
            existing_holes=[
                Hole(cx=0, cy=20, diameter=4.5, purpose="hole A"),
                Hole(cx=1, cy=20, diameter=4.5, purpose="hole B (overlaps A)"),
            ],
            fan_center=(0, -30),
            fan_bolt_spacing=32,
            fan_bolt_diameter=4.5,
            fan_airflow_diameter=20,
            cable_notch=None,
            min_wall_thickness=3.0,
        )
        with self.assertRaises(DesignIntentViolation):
            generate_fan_mount_bracket(bad)

    def test_hole_crowding_boundary_rejected(self):
        bad = FanMountBracketIntent(
            purpose="deliberately invalid: hole too close to the edge",
            envelope=Envelope(width=20, height=20, thickness=3),
            existing_holes=[Hole(cx=9.5, cy=0, diameter=4.5, purpose="crowds east edge")],
            fan_center=(0, 0),
            fan_bolt_spacing=6,
            fan_bolt_diameter=2,
            fan_airflow_diameter=4,
            cable_notch=None,
            min_wall_thickness=3.0,
        )
        with self.assertRaises(DesignIntentViolation):
            generate_fan_mount_bracket(bad)

    def test_hole_in_keep_out_notch_rejected(self):
        bad = FanMountBracketIntent(
            purpose="deliberately invalid: hole sits inside the cable keep-out",
            envelope=Envelope(width=70, height=70, thickness=3),
            existing_holes=[Hole(cx=-22.0, cy=-33.0, diameter=4.5, purpose="sits in the south notch")],
            fan_center=(0, 20),
            fan_bolt_spacing=32,
            fan_bolt_diameter=4.5,
            fan_airflow_diameter=20,
            cable_notch=EdgeNotch(edge="south", center_offset=-22.0, width=10.0, depth=5.0, purpose="cable clearance"),
            min_wall_thickness=3.0,
        )
        with self.assertRaises(DesignIntentViolation):
            generate_fan_mount_bracket(bad)

    def test_validation_status_is_honest(self):
        # The generator must never claim more than it actually did.
        self.assertTrue(self.status.geometry_proposed)
        self.assertTrue(self.status.constraints_checked)
        self.assertFalse(self.status.simulation_completed)
        self.assertFalse(self.status.prototype_manufactured)
        self.assertFalse(self.status.prototype_tested)
        self.assertFalse(self.status.externally_reviewed)
        self.assertFalse(self.status.validated_for_use)


if __name__ == "__main__":
    unittest.main()
