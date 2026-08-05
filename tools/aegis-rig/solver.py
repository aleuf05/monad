#!/usr/bin/env python3
"""Aegis-Monad rigging solver — Packet Beta Modules 1 and 2, over real files.

Module 1 (Skeletal Topology Solver) synthesises a joint chain from static
geometry. Module 2 (Automated Skinning) assigns vertex-to-bone weights
*per shell*, which is the whole point: VALIDATE established that every
asset in this corpus is fragmented (gasket 395 disjoint shells, the-monad
4,676), and Packet Beta correctly names weight bleeding across disjoint
meshes as the failure mode of proximity-based auto-weighting.

The anti-bleed rule, stated once: a shell whose axial span is shorter than
one bone's span is bound *rigidly* to a single joint. It moves as one
piece or not at all. Only shells that genuinely straddle joints get blended
weights, and then only between the joints they actually straddle. A loose
bolt cannot be half-owned by two bones that would pull it apart, because a
loose bolt is never given two bones.

Pure stdlib. Writes a real rigged .glb: skin, joint nodes, inverse bind
matrices, JOINTS_0 and WEIGHTS_0.
"""

from __future__ import annotations

import hashlib
import json
import struct
import subprocess
import sys
import time
from array import array
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "aegis-inspect"))
import inspector  # noqa: E402

CHUNK_JSON = 0x4E4F534A
CHUNK_BIN = 0x004E4942

# A shell shorter than this many bone-spans along the chain axis is rigid.
# 1.0 is not arbitrary: a shell that cannot reach from one joint to the next
# has no interior for a blend to happen in, so any blend it received would be
# bleed by definition.
RIGID_SPAN_FACTOR = 1.0

# Shell-grouping radius, as a fraction of bone_span. **Default 0.0 —
# disabled.** Kept as a documented negative result rather than deleted:
# grouping touching shells was the obvious fix for inter-part collision and
# it does not work with bounding-box adjacency. Union-find is transitive, and
# in interlocking geometry one chain of overlapping boxes links everything —
# measured on gasket, every epsilon above zero collapsed all 395 shells into
# a single group, and clipping did not improve even then (337 vs 334).
#
# Making this useful needs true surface proximity (vertex-level distance via
# a spatial grid), not box overlap. Until then the honest setting is off.
ADJACENCY_FACTOR = 0.0

DEFAULT_JOINTS = 5
WEIGHT_EPSILON = 1e-5

# Admiral's ruling, 2026-08-05: Rust for the maths, Python only where
# performance is not critical. The Rust core owns union-find, skeleton fitting
# and weight solving; everything in this file is glTF I/O. The Python
# implementations below stay as a reference and a fallback — test_parity.py
# holds the two to the same answers, which is the only thing that makes a
# rewrite in a second language safe to trust.
CORE_BINARY = Path(__file__).resolve().parent / "rust" / "target" / "release" / "aegis-rig-core"
CORE_MAGIC = b"ARIG"
CORE_VERSION = 1


class RigError(RuntimeError):
    pass


# --- reading ----------------------------------------------------------------

def _split_glb(data: bytes) -> tuple[dict, bytes, int]:
    if len(data) < 20 or data[:4] != b"glTF":
        raise RigError("not a binary glTF (.glb) file")
    gltf, bin_body, bin_offset = None, b"", 0
    offset = 12
    while offset + 8 <= len(data):
        chunk_len, chunk_type = struct.unpack("<II", data[offset:offset + 8])
        body = data[offset + 8:offset + 8 + chunk_len]
        if chunk_type == CHUNK_JSON:
            gltf = json.loads(body.decode("utf-8", "replace"))
        elif chunk_type == CHUNK_BIN:
            bin_body, bin_offset = body, offset + 8
        offset += 8 + chunk_len + (-chunk_len % 4)
    if gltf is None:
        raise RigError("no glTF JSON chunk")
    if not bin_body:
        raise RigError("no binary chunk — external buffers are not supported")
    return gltf, bin_body, bin_offset


def _read_positions(gltf: dict, blob: bytes, accessor_index: int) -> list[tuple]:
    accessor = gltf["accessors"][accessor_index]
    if accessor.get("componentType") != 5126 or accessor.get("type") != "VEC3":
        raise RigError("POSITION accessor is not float VEC3")
    view = gltf["bufferViews"][accessor["bufferView"]]
    start = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
    count = accessor["count"]
    stride = view.get("byteStride") or 12
    if stride == 12:
        flat = struct.unpack_from(f"<{count * 3}f", blob, start)
        return [tuple(flat[i:i + 3]) for i in range(0, len(flat), 3)]
    return [struct.unpack_from("<3f", blob, start + i * stride) for i in range(count)]


# --- Module 1: skeletal topology -------------------------------------------

def _joint_names(count: int) -> list[str]:
    """Packet Beta's semantic anchors (@Root, @Spine, @Head) presuppose an
    anatomical labelling this corpus does not carry — these are mechanical
    parts, not characters. The chain is named by what it actually is."""
    return ["@Root"] + [f"@Axis.{i:03d}" for i in range(1, count - 1)] + ["@Tip"]


def verify_acyclic(parents: list[int]) -> bool:
    """Packet Beta names DAG acyclicity as the structural check on a joint
    hierarchy. A chain can only cycle through a malformed parent table, but
    the check is cheap and the solver is meant to generalise past chains."""
    for start in range(len(parents)):
        seen, node = set(), start
        while node != -1:
            if node in seen:
                return False
            seen.add(node)
            node = parents[node]
    return True


def solve_skeleton(positions: list[tuple], joint_count: int = DEFAULT_JOINTS) -> dict:
    """Fit a joint chain to the geometry's dominant axis.

    Joints sit at the centroid of their axial slice rather than on the
    bounding-box centreline, so the chain follows where the mass actually is.
    For a symmetric part that is the same line; for a bent one it is not.
    """
    if joint_count < 2:
        raise RigError("a chain needs at least two joints")
    lo = [min(p[i] for p in positions) for i in range(3)]
    hi = [max(p[i] for p in positions) for i in range(3)]
    extent = [hi[i] - lo[i] for i in range(3)]
    axis = extent.index(max(extent))
    if extent[axis] <= 0:
        raise RigError("degenerate geometry — zero extent on every axis")

    span = extent[axis]
    step = span / joint_count
    sums = [[0.0, 0.0, 0.0] for _ in range(joint_count)]
    counts = [0] * joint_count
    for p in positions:
        slot = int((p[axis] - lo[axis]) / step)
        slot = min(max(slot, 0), joint_count - 1)
        for i in range(3):
            sums[slot][i] += p[i]
        counts[slot] += 1

    joints = []
    for j in range(joint_count):
        centre_axis = lo[axis] + step * (j + 0.5)
        if counts[j]:
            point = [sums[j][i] / counts[j] for i in range(3)]
            # Pin the axial coordinate to the slice centre; the centroid only
            # decides where the chain sits *off* axis.
            point[axis] = centre_axis
        else:
            point = [(lo[i] + hi[i]) / 2 for i in range(3)]
            point[axis] = centre_axis
        joints.append(tuple(point))

    parents = [-1] + list(range(joint_count - 1))
    if not verify_acyclic(parents):
        raise RigError("joint hierarchy is not acyclic")

    return {
        "axis": axis,
        "axis_name": "XYZ"[axis],
        "axis_min": lo[axis],
        "axis_max": hi[axis],
        "bone_span": step,
        "joints": joints,
        "parents": parents,
        "names": _joint_names(joint_count),
        "bounds": {"min": lo, "max": hi},
    }


# --- Module 2: shell-aware skinning ----------------------------------------

def group_shells(positions: list[tuple], labels: list[int], shell_count: int,
                 epsilon: float) -> tuple[list[int], int]:
    """Merge shells whose bounding boxes sit within epsilon into rigid groups.

    Python reference for the Rust kernel; same result, O(S^2) either way.
    """
    lo = [[float("inf")] * 3 for _ in range(shell_count)]
    hi = [[float("-inf")] * 3 for _ in range(shell_count)]
    for index, label in enumerate(labels):
        p = positions[index]
        for i in range(3):
            if p[i] < lo[label][i]:
                lo[label][i] = p[i]
            if p[i] > hi[label][i]:
                hi[label][i] = p[i]

    parent = list(range(shell_count))

    def find(x: int) -> int:
        root = x
        while parent[root] != root:
            root = parent[root]
        while parent[x] != root:
            parent[x], x = root, parent[x]
        return root

    for a in range(shell_count):
        for b in range(a + 1, shell_count):
            if all(lo[a][i] - epsilon <= hi[b][i] and lo[b][i] - epsilon <= hi[a][i]
                   for i in range(3)):
                ra, rb = find(a), find(b)
                if ra != rb:
                    parent[rb] = ra

    dense: dict[int, int] = {}
    group_of = [0] * shell_count
    for s in range(shell_count):
        root = find(s)
        label = dense.get(root)
        if label is None:
            label = dense[root] = len(dense)
        group_of[s] = label
    return group_of, len(dense)


def solve_weights(positions: list[tuple], labels: list[int], skeleton: dict,
                  adjacency_factor: float = ADJACENCY_FACTOR) -> dict:
    """Assign at most two influences per vertex, never across a shell that
    cannot support a blend. Returns joint indices, weights, and the evidence
    for what it decided."""
    axis = skeleton["axis"]
    joints = skeleton["joints"]
    joint_axis = [j[axis] for j in joints]
    rigid_threshold = skeleton["bone_span"] * RIGID_SPAN_FACTOR

    shell_count = (max(labels) + 1) if labels else 0
    if adjacency_factor > 0.0:
        group_of, group_count = group_shells(
            positions, labels, shell_count, skeleton["bone_span"] * adjacency_factor)
    else:
        group_of, group_count = list(range(shell_count)), shell_count

    shells: dict[int, list[int]] = {}
    for index, label in enumerate(labels):
        shells.setdefault(group_of[label], []).append(index)

    joint_ids = array("H", bytes(8 * len(positions)))
    weights = array("f", [0.0]) * (4 * len(positions))

    rigid_shells = blended_shells = 0
    rigid_vertices = blended_vertices = 0

    for members in shells.values():
        coords = [positions[i][axis] for i in members]
        lo, hi = min(coords), max(coords)

        if (hi - lo) < rigid_threshold:
            # Whole shell, one bone. This is the bleed guard.
            centre = sum(coords) / len(coords)
            nearest = min(range(len(joints)), key=lambda j: abs(joint_axis[j] - centre))
            rigid_shells += 1
            rigid_vertices += len(members)
            for i in members:
                joint_ids[4 * i] = nearest
                weights[4 * i] = 1.0
            continue

        blended_shells += 1
        blended_vertices += len(members)
        for i in members:
            t = positions[i][axis]
            # Bracketing joints, clamped to the ends of the chain.
            upper = 0
            while upper < len(joints) and joint_axis[upper] < t:
                upper += 1
            if upper == 0:
                joint_ids[4 * i] = 0
                weights[4 * i] = 1.0
                continue
            if upper >= len(joints):
                joint_ids[4 * i] = len(joints) - 1
                weights[4 * i] = 1.0
                continue
            a, b = upper - 1, upper
            gap = joint_axis[b] - joint_axis[a]
            frac = 0.0 if gap <= 0 else (t - joint_axis[a]) / gap
            frac = min(max(frac, 0.0), 1.0)
            joint_ids[4 * i], joint_ids[4 * i + 1] = a, b
            # Normalise explicitly rather than trusting the arithmetic: the
            # weight-sum invariant is the one Packet Beta calls out, and
            # float32 storage rounds after we are done here.
            total = (1.0 - frac) + frac
            weights[4 * i] = (1.0 - frac) / total
            weights[4 * i + 1] = frac / total

    worst = 0.0
    unweighted = 0
    for i in range(len(positions)):
        total = weights[4 * i] + weights[4 * i + 1] + weights[4 * i + 2] + weights[4 * i + 3]
        if total == 0.0:
            unweighted += 1
        worst = max(worst, abs(total - 1.0))

    return {
        "joint_ids": joint_ids,
        "weights": weights,
        "shells": shell_count,
        "groups": group_count,
        "rigid_shells": rigid_shells,
        "blended_shells": blended_shells,
        "rigid_vertices": rigid_vertices,
        "blended_vertices": blended_vertices,
        "max_weight_error": worst,
        "unweighted_vertices": unweighted,
        "weights_sum_to_one": worst <= WEIGHT_EPSILON and unweighted == 0,
    }


# --- engine dispatch --------------------------------------------------------

def core_available() -> bool:
    return CORE_BINARY.is_file()


def solve_via_rust(positions: list[tuple], indices, joint_count: int,
                   adjacency_factor: float = ADJACENCY_FACTOR) -> tuple[dict, dict]:
    """Hand the hot path to the Rust core over a binary pipe.

    JSON would put the cost back into the parsing we moved to Rust to avoid,
    so positions and indices go across as raw little-endian arrays.
    """
    header = CORE_MAGIC + struct.pack(
        "<IIIIf", CORE_VERSION, len(positions), len(indices), joint_count,
        adjacency_factor)
    pos = array("f")
    for p in positions:
        pos.extend(p)
    idx = array("I", indices)
    payload = header + pos.tobytes() + idx.tobytes()

    result = subprocess.run([str(CORE_BINARY)], input=payload,
                            stdout=subprocess.PIPE, check=False)
    out = result.stdout
    if len(out) < 4:
        raise RigError("rigging core returned nothing")
    json_len = struct.unpack_from("<I", out, 0)[0]
    report = json.loads(out[4:4 + json_len].decode("utf-8"))
    if not report.get("ok"):
        raise RigError(f"rigging core: {report.get('error', 'unknown failure')}")

    count = len(positions)
    offset = 4 + json_len
    joint_ids = array("H")
    joint_ids.frombytes(out[offset:offset + count * 8])
    offset += count * 8
    weights = array("f")
    weights.frombytes(out[offset:offset + count * 16])

    joints = [tuple(j) for j in report["joints"]]
    skeleton = {
        "axis": report["axis"],
        "axis_name": "XYZ"[report["axis"]],
        "axis_min": report["axis_min"],
        "axis_max": report["axis_max"],
        "bone_span": report["bone_span"],
        "joints": joints,
        "parents": [-1] + list(range(len(joints) - 1)),
        "names": _joint_names(len(joints)),
    }
    skin = {
        "joint_ids": joint_ids,
        "weights": weights,
        "shells": report["shells"],
        "groups": report.get("groups", report["shells"]),
        "rigid_shells": report["rigid_shells"],
        "blended_shells": report["blended_shells"],
        "rigid_vertices": report["rigid_vertices"],
        "blended_vertices": report["blended_vertices"],
        "max_weight_error": report["max_weight_error"],
        "unweighted_vertices": report["unweighted_vertices"],
        "weights_sum_to_one": (report["max_weight_error"] <= WEIGHT_EPSILON
                               and report["unweighted_vertices"] == 0),
    }
    return skeleton, skin


def solve_core(positions: list[tuple], indices, joint_count: int,
               engine: str = "auto",
               adjacency_factor: float = ADJACENCY_FACTOR) -> tuple[dict, dict, str]:
    """Run the maths. `engine` is "auto" (Rust if built), "rust", or "python"."""
    if engine not in ("auto", "rust", "python"):
        raise RigError(f"unknown engine {engine!r}")
    if engine == "rust" and not core_available():
        raise RigError("rigging core is not built — run cargo build --release")
    if engine != "python" and core_available():
        skeleton, skin = solve_via_rust(positions, indices, joint_count, adjacency_factor)
        return skeleton, skin, "rust"

    labels = inspector.connected_components(indices, len(positions))
    skeleton = solve_skeleton(positions, joint_count)
    return skeleton, solve_weights(positions, labels, skeleton, adjacency_factor), "python"


# --- writing ----------------------------------------------------------------

def _pad4(blob: bytes, fill: bytes = b"\x00") -> bytes:
    return blob + fill * (-len(blob) % 4)


def _inverse_bind_matrices(joints: list[tuple]) -> bytes:
    """Joints carry translation only, so the inverse bind matrix is a
    translation by the negated world position. Column-major, per glTF."""
    out = array("f")
    for x, y, z in joints:
        out.extend((1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, -x, -y, -z, 1))
    return out.tobytes()


def write_rigged(source: Path, dest: Path, joint_count: int = DEFAULT_JOINTS,
                 engine: str = "auto",
                 adjacency_factor: float = ADJACENCY_FACTOR) -> dict:
    data = source.read_bytes()
    gltf, blob, _ = _split_glb(data)

    meshes = gltf.get("meshes", [])
    if not meshes or not meshes[0].get("primitives"):
        raise RigError("no mesh primitives to rig")
    mesh_index = 0
    prim = meshes[mesh_index]["primitives"][0]
    if len(meshes) > 1 or len(meshes[mesh_index]["primitives"]) > 1:
        raise RigError("solver v0.1 rigs a single-primitive mesh; this asset has more")

    pos_accessor = prim["attributes"].get("POSITION")
    idx_accessor = prim.get("indices")
    if pos_accessor is None or idx_accessor is None:
        raise RigError("primitive lacks POSITION or indices")

    positions = _read_positions(gltf, blob, pos_accessor)
    indices = inspector._read_indices(gltf, blob, 0, idx_accessor)

    started = time.perf_counter()
    skeleton, skin, engine_used = solve_core(
        positions, indices, joint_count, engine, adjacency_factor)
    solve_ms = (time.perf_counter() - started) * 1000

    if not skin["weights_sum_to_one"]:
        raise RigError(
            f"weight validation failed: max error {skin['max_weight_error']:.3e}, "
            f"{skin['unweighted_vertices']} unweighted vertices"
        )

    # Append three blocks to the existing buffer. Nothing already in the file
    # moves, so every accessor that was valid before is still valid.
    buffer_len = gltf["buffers"][0]["byteLength"]
    tail = bytearray(blob[:buffer_len])

    def append(payload: bytes, target: int | None) -> int:
        while len(tail) % 4:
            tail.append(0)
        offset = len(tail)
        tail.extend(payload)
        view = {"buffer": 0, "byteOffset": offset, "byteLength": len(payload)}
        if target is not None:
            view["target"] = target
        gltf.setdefault("bufferViews", []).append(view)
        return len(gltf["bufferViews"]) - 1

    joints_view = append(skin["joint_ids"].tobytes(), 34962)
    weights_view = append(skin["weights"].tobytes(), 34962)
    ibm_view = append(_inverse_bind_matrices(skeleton["joints"]), None)

    accessors = gltf.setdefault("accessors", [])
    vertex_count = len(positions)
    accessors.append({"bufferView": joints_view, "componentType": 5123,
                      "count": vertex_count, "type": "VEC4"})
    joints_accessor = len(accessors) - 1
    accessors.append({"bufferView": weights_view, "componentType": 5126,
                      "count": vertex_count, "type": "VEC4"})
    weights_accessor = len(accessors) - 1
    accessors.append({"bufferView": ibm_view, "componentType": 5126,
                      "count": len(skeleton["joints"]), "type": "MAT4"})
    ibm_accessor = len(accessors) - 1

    prim["attributes"]["JOINTS_0"] = joints_accessor
    prim["attributes"]["WEIGHTS_0"] = weights_accessor

    # Joint nodes. glTF node translations are relative to the parent, so the
    # chain stores deltas even though the solver worked in world space.
    nodes = gltf.setdefault("nodes", [])
    first_joint_node = len(nodes)
    for j, point in enumerate(skeleton["joints"]):
        parent = skeleton["parents"][j]
        origin = skeleton["joints"][parent] if parent >= 0 else (0.0, 0.0, 0.0)
        node = {
            "name": skeleton["names"][j],
            "translation": [point[i] - origin[i] for i in range(3)],
        }
        if j + 1 < len(skeleton["joints"]):
            node["children"] = [first_joint_node + j + 1]
        nodes.append(node)

    joint_nodes = [first_joint_node + j for j in range(len(skeleton["joints"]))]
    gltf.setdefault("skins", []).append({
        "name": "AegisRig",
        "joints": joint_nodes,
        "skeleton": first_joint_node,
        "inverseBindMatrices": ibm_accessor,
    })
    skin_index = len(gltf["skins"]) - 1

    mesh_node = next((i for i, n in enumerate(nodes) if n.get("mesh") == mesh_index), None)
    if mesh_node is None:
        raise RigError("no node references the mesh")
    nodes[mesh_node]["skin"] = skin_index

    # The joint root has to be in the scene or the skin is unreachable.
    scenes = gltf.setdefault("scenes", [{"nodes": [mesh_node]}])
    scene = scenes[gltf.get("scene", 0)]
    scene.setdefault("nodes", []).append(first_joint_node)

    generator = gltf.setdefault("asset", {}).get("generator", "unknown")
    gltf["asset"]["generator"] = f"{generator} + aegis-rig 0.1"

    gltf["buffers"][0]["byteLength"] = len(tail)

    json_chunk = _pad4(json.dumps(gltf, separators=(",", ":")).encode("utf-8"), b" ")
    bin_chunk = _pad4(bytes(tail))
    total = 12 + 8 + len(json_chunk) + 8 + len(bin_chunk)
    out = bytearray(b"glTF")
    out += struct.pack("<II", 2, total)
    out += struct.pack("<II", len(json_chunk), CHUNK_JSON) + json_chunk
    out += struct.pack("<II", len(bin_chunk), CHUNK_BIN) + bin_chunk

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(bytes(out))

    return {
        "ok": True,
        "source": str(source),
        "dest": str(dest),
        "source_sha256": hashlib.sha256(data).hexdigest(),
        "rigged_sha256": hashlib.sha256(bytes(out)).hexdigest(),
        "source_bytes": len(data),
        "rigged_bytes": len(out),
        "vertices": vertex_count,
        "joint_count": len(skeleton["joints"]),
        "joint_names": skeleton["names"],
        "joint_positions": [[round(c, 6) for c in p] for p in skeleton["joints"]],
        "axis": skeleton["axis_name"],
        "bone_span": round(skeleton["bone_span"], 6),
        "shells": skin["shells"],
        "groups": skin.get("groups", skin["shells"]),
        "adjacency_factor": adjacency_factor,
        "rigid_shells": skin["rigid_shells"],
        "blended_shells": skin["blended_shells"],
        "rigid_vertices": skin["rigid_vertices"],
        "blended_vertices": skin["blended_vertices"],
        "max_weight_error": skin["max_weight_error"],
        "weights_sum_to_one": skin["weights_sum_to_one"],
        "engine": engine_used,
        "solve_ms": round(solve_ms, 2),
    }


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print("usage: solver.py <source.glb> <dest.glb> [joint_count]")
        return 2
    count = int(argv[3]) if len(argv) > 3 else DEFAULT_JOINTS
    print(json.dumps(write_rigged(Path(argv[1]), Path(argv[2]), count), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
