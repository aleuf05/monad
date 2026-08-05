#!/usr/bin/env python3
"""Deformation probe — Packet Beta Module 3, over a real rigged asset.

AUTHORIZE proves a rig is *valid*. This asks whether it is any *good*, by
posing it and looking for the artifacts a rigger actually looks for:
pinching, inverted faces, tearing, and parts driven into each other.

The last one is the interesting one on this corpus. A gasket rigged at 8
joints is 374 rigid shells hanging off a chain; bend the chain and those
shells swing into each other long before any single shell deforms badly.
That is the failure this corpus is actually prone to, and it is invisible
to a weight-sum check.

Python builds the pose matrices — a handful of 4x4s, where the language
does not matter — and the Rust kernel does the per-vertex work, per
doctrine 015.
"""

from __future__ import annotations

import json
import math
import struct
import subprocess
import sys
from array import array
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "aegis-inspect"))
import inspector  # noqa: E402
import solver  # noqa: E402

DEFORM_MAGIC = b"ADEF"
DEFORM_VERSION = 1

# Four bends, shallow to severe. A rig that survives 15 degrees and fails at
# 60 is telling you where its usable range ends, which is more useful than a
# single pass/fail at one arbitrary angle.
DEFAULT_ANGLES = (15.0, 30.0, 45.0, 60.0)


class DeformError(RuntimeError):
    pass


# --- small matrix helpers (column-major, glTF convention) -------------------

IDENTITY = (1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0, 0, 0, 0, 0, 1.0)


def mat_mul(a, b):
    """a @ b, both column-major 4x4 as flat 16-tuples."""
    out = [0.0] * 16
    for col in range(4):
        for row in range(4):
            out[col * 4 + row] = sum(a[k * 4 + row] * b[col * 4 + k] for k in range(4))
    return tuple(out)


def mat_translate(t):
    return (1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, t[0], t[1], t[2], 1)


def mat_rotate(axis: int, angle: float):
    """Rotation about a world axis, by index."""
    c, s = math.cos(angle), math.sin(angle)
    if axis == 0:
        return (1, 0, 0, 0, 0, c, s, 0, 0, -s, c, 0, 0, 0, 0, 1)
    if axis == 1:
        return (c, 0, -s, 0, 0, 1, 0, 0, s, 0, c, 0, 0, 0, 0, 1)
    return (c, s, 0, 0, -s, c, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1)


def node_local(node: dict):
    if "matrix" in node:
        return tuple(node["matrix"])
    local = mat_translate(node.get("translation", (0.0, 0.0, 0.0)))
    scale = node.get("scale")
    if scale:
        local = mat_mul(local, (scale[0], 0, 0, 0, 0, scale[1], 0, 0,
                                0, 0, scale[2], 0, 0, 0, 0, 1))
    return local


# --- reading a rigged asset -------------------------------------------------

def _read_vec4(gltf, blob, accessor_index, kind):
    accessor = gltf["accessors"][accessor_index]
    view = gltf["bufferViews"][accessor["bufferView"]]
    start = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
    count = accessor["count"]
    component = accessor["componentType"]
    if kind == "joints":
        fmt = {5121: "B", 5123: "H"}.get(component)
        if fmt is None:
            raise DeformError(f"unsupported JOINTS_0 component type {component}")
        raw = struct.unpack_from(f"<{count * 4}{fmt}", blob, start)
        return array("H", raw)
    if component != 5126:
        raise DeformError("WEIGHTS_0 must be float for this probe")
    return array("f", struct.unpack_from(f"<{count * 4}f", blob, start))


def load_rig(path: Path) -> dict:
    gltf, blob, _ = solver._split_glb(path.read_bytes())
    skins = gltf.get("skins") or []
    if not skins:
        raise DeformError("asset has no skin — nothing to pose")
    skin = skins[0]

    prim = None
    for mesh in gltf.get("meshes", []):
        for candidate in mesh.get("primitives", []):
            if "JOINTS_0" in candidate.get("attributes", {}):
                prim = candidate
                break
        if prim:
            break
    if prim is None:
        raise DeformError("no primitive carries JOINTS_0")

    positions = solver._read_positions(gltf, blob, prim["attributes"]["POSITION"])
    indices = inspector._read_indices(gltf, blob, 0, prim["indices"])
    joint_ids = _read_vec4(gltf, blob, prim["attributes"]["JOINTS_0"], "joints")
    weights = _read_vec4(gltf, blob, prim["attributes"]["WEIGHTS_0"], "weights")

    nodes = gltf.get("nodes", [])
    joint_nodes = skin["joints"]

    parent_of = {}
    for index, node in enumerate(nodes):
        for child in node.get("children", []):
            parent_of[child] = index

    def world(node_index):
        chain = []
        current = node_index
        while current is not None:
            chain.append(current)
            current = parent_of.get(current)
        matrix = IDENTITY
        for index in reversed(chain):
            matrix = mat_mul(matrix, node_local(nodes[index]))
        return matrix

    rest_world = [world(n) for n in joint_nodes]

    ibm_index = skin.get("inverseBindMatrices")
    if ibm_index is None:
        inverse_bind = [IDENTITY] * len(joint_nodes)
    else:
        accessor = gltf["accessors"][ibm_index]
        view = gltf["bufferViews"][accessor["bufferView"]]
        start = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
        flat = struct.unpack_from(f"<{accessor['count'] * 16}f", blob, start)
        inverse_bind = [tuple(flat[i * 16:(i + 1) * 16]) for i in range(accessor["count"])]

    return {
        "positions": positions,
        "indices": indices,
        "joint_ids": joint_ids,
        "weights": weights,
        "joint_nodes": joint_nodes,
        "rest_world": rest_world,
        "inverse_bind": inverse_bind,
        "parent_of": parent_of,
        "nodes": nodes,
    }


# --- posing -----------------------------------------------------------------

def build_poses(rig: dict, angles=DEFAULT_ANGLES) -> tuple[list, int]:
    """Bend the chain progressively: the root holds still and each joint down
    the chain adds another share of the angle, which is what a limb does."""
    joint_nodes = rig["joint_nodes"]
    origins = [(m[12], m[13], m[14]) for m in rig["rest_world"]]

    # Chain direction from the joint positions; rotate about a world axis
    # perpendicular to it, so the bend is visible rather than a twist.
    spread = [max(p[i] for p in origins) - min(p[i] for p in origins) for i in range(3)]
    chain_axis = spread.index(max(spread))
    bend_axis = (chain_axis + 2) % 3

    parent_of = rig["parent_of"]
    index_of = {node: i for i, node in enumerate(joint_nodes)}
    count = len(joint_nodes)

    poses = []
    for degrees in angles:
        total = math.radians(degrees)
        posed_world = [None] * count
        for i, node in enumerate(joint_nodes):
            share = total / max(count - 1, 1)
            local = node_local(rig["nodes"][node])
            # Rotate in the joint's own frame: translate out, spin, translate
            # back is implicit because the local matrix already carries the
            # offset from the parent.
            local = mat_mul(local, mat_rotate(bend_axis, share if i > 0 else 0.0))
            parent_node = parent_of.get(node)
            parent_index = index_of.get(parent_node)
            if parent_index is None:
                posed_world[i] = local
            else:
                posed_world[i] = mat_mul(posed_world[parent_index], local)
        poses.append([mat_mul(posed_world[i], rig["inverse_bind"][i])
                      for i in range(count)])
    return poses, bend_axis


# --- the probe --------------------------------------------------------------

def probe(path: Path, angles=DEFAULT_ANGLES) -> dict:
    if not solver.core_available():
        raise DeformError("rigging core is not built — run cargo build --release")

    rig = load_rig(path)
    poses, bend_axis = build_poses(rig, angles)

    vertices = len(rig["positions"])
    joints = len(rig["joint_nodes"])
    header = DEFORM_MAGIC + struct.pack(
        "<IIIII", DEFORM_VERSION, vertices, len(rig["indices"]), joints, len(poses))

    pos = array("f")
    for p in rig["positions"]:
        pos.extend(p)
    idx = array("I", rig["indices"])
    mats = array("f")
    for pose in poses:
        for matrix in pose:
            mats.extend(matrix)

    payload = (header + pos.tobytes() + idx.tobytes()
               + rig["joint_ids"].tobytes() + rig["weights"].tobytes()
               + mats.tobytes())

    result = subprocess.run([str(solver.CORE_BINARY)], input=payload,
                            stdout=subprocess.PIPE, check=False)
    out = result.stdout
    if len(out) < 4:
        raise DeformError("deform kernel returned nothing")
    json_len = struct.unpack_from("<I", out, 0)[0]
    report = json.loads(out[4:4 + json_len].decode("utf-8"))
    if not report.get("ok"):
        raise DeformError(report.get("error", "deform kernel failed"))

    triangles = report["triangles"]
    graded = []
    for degrees, pose in zip(angles, report["poses"]):
        graded.append({**pose, "degrees": degrees, **grade(pose, triangles)})

    worst = max(graded, key=lambda g: ("fail", "warn", "pass").index(g["verdict"]) * -1)
    return {
        "ok": True,
        "asset": path.name,
        "triangles": triangles,
        "shells": report["shells"],
        "joints": joints,
        "bend_axis": "XYZ"[bend_axis],
        "poses": graded,
        "verdict": worst["verdict"],
        "note": worst["reason"],
    }


def grade(pose: dict, triangles: int) -> dict:
    """Thresholds as fractions of the mesh, not absolute counts — otherwise a
    million-triangle asset fails for artifacts a small one is forgiven."""
    if triangles <= 0:
        return {"verdict": "fail", "reason": "no triangles to measure"}

    inverted = pose["inverted"] / triangles
    collapsed = pose["collapsed"] / triangles
    torn = pose["torn"] / max(triangles * 3, 1)

    if inverted > 0.001:
        return {"verdict": "fail",
                "reason": f"{pose['inverted']:,} inverted faces "
                          f"({inverted * 100:.2f}%) — surface turns inside out"}
    if collapsed > 0.05:
        return {"verdict": "fail",
                "reason": f"{pose['collapsed']:,} collapsed faces "
                          f"({collapsed * 100:.1f}%) — severe pinching"}
    if pose["clipping_pairs"] > 0:
        return {"verdict": "warn",
                "reason": f"{pose['clipping_pairs']:,} shell pairs newly "
                          "overlapping — parts driven into each other"}
    if collapsed > 0.01 or torn > 0.01:
        return {"verdict": "warn",
                "reason": f"{pose['collapsed']:,} pinched, {pose['torn']:,} torn edges"}
    return {"verdict": "pass",
            "reason": f"no inversion, no clipping, max stretch "
                      f"{pose['max_stretch']:.2f}x"}


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: deform.py <rigged.glb> [angle ...]")
        return 2
    angles = tuple(float(a) for a in argv[2:]) or DEFAULT_ANGLES
    print(json.dumps(probe(Path(argv[1]), angles), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
