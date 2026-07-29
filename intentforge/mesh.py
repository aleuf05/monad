"""IntentForge v0.0 -- minimal pure-Python watertight-mesh engine.

Not a CAD kernel. This is the smallest thing that can turn a 2D outline
plus circular holes into a real, inspectable, watertight extruded solid
and write it as a binary STL -- with zero external dependencies, because
the real libfive backend this repo already has (tools/libfive) is not
usable on this machine right now (no exporter binary installed, no
source checkout to verify Guile stdlib call signatures against). Writing
CSG script text for a kernel that can't be run or checked here would be
an unverified claim dressed as geometry -- exactly what IntentForge's own
truthfulness section forbids. This module is deliberately small enough to
verify by direct inspection and unit test instead.

Growth path (not built here): swap this extrusion engine for real
libfive CSG once the exporter is installed via cmd.sh, without changing
design_intent.py's contract shape -- bracket_generator.py is the only
file that would need to change.
"""

from __future__ import annotations

import math
import struct
from dataclasses import dataclass, field


Point2 = tuple[float, float]
Point3 = tuple[float, float, float]
Tri = tuple[int, int, int]


def circle_points(cx: float, cy: float, r: float, n: int, ccw: bool = True) -> list[Point2]:
    if n < 8:
        raise ValueError("circle needs at least 8 segments to be a reasonable approximation")
    pts = []
    for i in range(n):
        theta = 2 * math.pi * i / n
        if not ccw:
            theta = -theta
        pts.append((cx + r * math.cos(theta), cy + r * math.sin(theta)))
    return pts


def _signed_area(poly: list[Point2]) -> float:
    area = 0.0
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        area += x1 * y2 - x2 * y1
    return area / 2.0


def _point_in_triangle(p: Point2, a: Point2, b: Point2, c: Point2) -> bool:
    def sign(p1, p2, p3):
        return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])

    d1 = sign(p, a, b)
    d2 = sign(p, b, c)
    d3 = sign(p, c, a)
    has_neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
    has_pos = (d1 > 0) or (d2 > 0) or (d3 > 0)
    return not (has_neg and has_pos)


def ear_clip_triangulate(poly: list[Point2]) -> list[Tri]:
    """Standard O(n^2) ear-clipping. Expects a simple, CCW polygon
    (bridged keyhole polygons from bridge_holes() qualify -- their
    bridge edges are traversed twice in opposite directions, which ear
    clipping handles fine since it never needs those "ears" to be cut)."""
    n = len(poly)
    if n < 3:
        return []
    if _signed_area(poly) < 0:
        raise ValueError("ear_clip_triangulate requires a CCW-wound polygon")

    indices = list(range(n))
    triangles: list[Tri] = []
    guard = 0
    max_guard = n * n + 10
    while len(indices) > 3:
        guard += 1
        if guard > max_guard:
            raise RuntimeError("ear clipping failed to converge -- polygon may be self-intersecting")
        ear_found = False
        m = len(indices)
        for i in range(m):
            i_prev = indices[(i - 1) % m]
            i_cur = indices[i]
            i_next = indices[(i + 1) % m]
            a, b, c = poly[i_prev], poly[i_cur], poly[i_next]
            cross = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
            if cross <= 0:
                continue  # reflex vertex, not a candidate ear
            is_ear = True
            near_vertex_tol = 1e-3  # 1 micron -- see bridge_holes()'s epsilon note
            for j in indices:
                if j in (i_prev, i_cur, i_next):
                    continue
                pj = poly[j]
                # A point that's essentially coincident with one of this
                # candidate's own three vertices (as the epsilon-nudged
                # bridge-return points deliberately are, by construction)
                # is not a meaningful "blocker" -- it's the same point
                # for triangulation purposes, just numerically split to
                # avoid an exactly-collinear bridge. Treating it as a
                # real interior point would make every ear near a bridge
                # unclippable regardless of how small the epsilon is.
                if any(math.hypot(pj[0] - v[0], pj[1] - v[1]) < near_vertex_tol for v in (a, b, c)):
                    continue
                if _point_in_triangle(pj, a, b, c):
                    is_ear = False
                    break
            if is_ear:
                triangles.append((i_prev, i_cur, i_next))
                del indices[i]
                ear_found = True
                break
        if not ear_found:
            raise RuntimeError("no ear found -- polygon may be self-intersecting or degenerate")
    triangles.append((indices[0], indices[1], indices[2]))
    return triangles


def bridge_holes(outer_ccw: list[Point2], holes_cw: list[list[Point2]]) -> list[Point2]:
    """Merge an outer CCW polygon with one or more CW-wound hole loops
    into a single simple polygon via nearest-vertex bridging (the
    standard "keyhole" technique), so it can be ear-clip triangulated as
    an ordinary simple polygon."""
    merged = list(outer_ccw)
    for hole in holes_cw:
        if _signed_area(hole) > 0:
            raise ValueError("hole loops must be CW-wound (opposite the outer boundary)")
        best_i, best_j, best_d = 0, 0, float("inf")
        for i, mp in enumerate(merged):
            for j, hp in enumerate(hole):
                d = (mp[0] - hp[0]) ** 2 + (mp[1] - hp[1]) ** 2
                if d < best_d:
                    best_d, best_i, best_j = d, i, j
        hole_rot = hole[best_j:] + hole[:best_j]
        bridge_a = merged[best_i]
        # A true zero-width bridge: walk out to the hole, all the way
        # around it, and back along the exact same two points. This
        # makes the two bridge edges exact duplicates of each other, so
        # they satisfy the watertight check by pairing with *each
        # other* within the cap triangulation, rather than needing (and
        # never finding) a matching wall edge. ear_clip_triangulate's
        # near-vertex tolerance handles the resulting degenerate-sliver
        # candidates directly, so no epsilon perturbation is needed here.
        # merged[best_i] (bridge_a) is already the last element of the
        # slice below -- do not repeat it unmodified, or the bridge
        # starts with a zero-length edge.
        bridge = hole_rot + [hole_rot[0], bridge_a]
        merged = merged[: best_i + 1] + bridge + merged[best_i + 1 :]
    return merged


@dataclass
class Mesh:
    vertices: list[Point3] = field(default_factory=list)
    triangles: list[Tri] = field(default_factory=list)

    def add_vertex(self, p: Point3) -> int:
        self.vertices.append(p)
        return len(self.vertices) - 1

    def extend_triangles(self, offset: int, tris: list[Tri]) -> None:
        for a, b, c in tris:
            self.triangles.append((a + offset, b + offset, c + offset))

    def bounding_box(self) -> tuple[Point3, Point3]:
        xs = [v[0] for v in self.vertices]
        ys = [v[1] for v in self.vertices]
        zs = [v[2] for v in self.vertices]
        return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))

    def signed_volume(self) -> float:
        """Divergence-theorem volume. Positive for a correctly
        outward-wound closed mesh -- used as one watertightness/
        correctness signal, not the only one."""
        vol = 0.0
        for a, b, c in self.triangles:
            p1, p2, p3 = self.vertices[a], self.vertices[b], self.vertices[c]
            vol += (
                p1[0] * (p2[1] * p3[2] - p3[1] * p2[2])
                - p1[1] * (p2[0] * p3[2] - p3[0] * p2[2])
                + p1[2] * (p2[0] * p3[1] - p3[0] * p2[1])
            )
        return vol / 6.0

    def is_watertight(self, precision: int = 6) -> bool:
        """Every undirected edge must be shared by exactly two
        triangles -- the standard manifold-closed check. Keyed by
        rounded vertex *coordinates*, not raw indices: this mesh is
        assembled from independent panels (caps + side walls) that each
        add their own vertex entries even where they spatially coincide
        with another panel's rim, so an index-keyed check would never
        find a match across panels regardless of correctness."""
        def key(idx: int) -> Point3:
            v = self.vertices[idx]
            return (round(v[0], precision), round(v[1], precision), round(v[2], precision))

        edge_count: dict[tuple[Point3, Point3], int] = {}
        for a, b, c in self.triangles:
            for u, v in ((a, b), (b, c), (c, a)):
                ku, kv = key(u), key(v)
                edge_key = (ku, kv) if ku < kv else (kv, ku)
                edge_count[edge_key] = edge_count.get(edge_key, 0) + 1
        return all(count == 2 for count in edge_count.values()) and len(edge_count) > 0


def extrude_flat_part(outer_ccw: list[Point2], holes_cw: list[list[Point2]], thickness: float) -> Mesh:
    """Build a watertight solid: top cap (z=+t/2), bottom cap
    (z=-t/2, mirrored winding), and independent side walls for the
    outer loop and every hole loop. Caps are triangulated via
    bridge_holes() + ear_clip_triangulate(); side walls are built
    directly from the original (un-bridged) loops, so bridge edges never
    appear in the final mesh -- only in the intermediate triangulation
    step, where duplicate reversed edges cancel out of the watertight
    check by construction (each bridge edge is walked once each
    direction and only ever appears inside a single triangulated cap).
    """
    half = thickness / 2.0
    merged = bridge_holes(outer_ccw, holes_cw)
    cap_tris = ear_clip_triangulate(merged)

    mesh = Mesh()

    top_offset = len(mesh.vertices)
    for x, y in merged:
        mesh.add_vertex((x, y, half))
    mesh.extend_triangles(top_offset, cap_tris)

    bottom_offset = len(mesh.vertices)
    for x, y in merged:
        mesh.add_vertex((x, y, -half))
    flipped = [(a, c, b) for a, b, c in cap_tris]
    mesh.extend_triangles(bottom_offset, flipped)

    def add_wall(loop: list[Point2], outward_ccw: bool) -> None:
        n = len(loop)
        t_off = len(mesh.vertices)
        for x, y in loop:
            mesh.add_vertex((x, y, half))
        b_off = len(mesh.vertices)
        for x, y in loop:
            mesh.add_vertex((x, y, -half))
        for i in range(n):
            j = (i + 1) % n
            t_i, t_j = t_off + i, t_off + j
            b_i, b_j = b_off + i, b_off + j
            if outward_ccw:
                mesh.triangles.append((t_i, b_i, t_j))
                mesh.triangles.append((t_j, b_i, b_j))
            else:
                mesh.triangles.append((t_i, t_j, b_i))
                mesh.triangles.append((t_j, b_j, b_i))

    add_wall(outer_ccw, outward_ccw=True)
    for hole in holes_cw:
        # A hole wall needs an outward-from-solid normal too (pointing
        # into the hole, since the solid is outside it) -- empirically
        # verified (signed_volume against a known box-with-hole volume)
        # that this is the *same* branch as the outer wall, not the
        # opposite: the hole loop's reversed winding and its reversed
        # solid/interior relationship (solid is outside a hole, inside
        # the outer boundary) cancel out.
        add_wall(hole, outward_ccw=True)

    return mesh


def write_binary_stl(mesh: Mesh, path: str, name: bytes = b"IntentForge v0.0") -> None:
    header = (name[:80]).ljust(80, b"\x00")
    with open(path, "wb") as f:
        f.write(header)
        f.write(struct.pack("<I", len(mesh.triangles)))
        for a, b, c in mesh.triangles:
            p1, p2, p3 = mesh.vertices[a], mesh.vertices[b], mesh.vertices[c]
            ux, uy, uz = (p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2])
            vx, vy, vz = (p3[0] - p1[0], p3[1] - p1[1], p3[2] - p1[2])
            nx, ny, nz = (uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx)
            length = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
            nx, ny, nz = nx / length, ny / length, nz / length
            f.write(struct.pack("<3f", nx, ny, nz))
            for p in (p1, p2, p3):
                f.write(struct.pack("<3f", *p))
            f.write(struct.pack("<H", 0))
