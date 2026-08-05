#!/usr/bin/env python3
"""Aegis-Monad INSPECT — read what the geometry corpus actually is.

Per MSIR-M3-Q2 (answered D): D_t is 3D assets. Before a rigging solver
can be built, something has to say what is actually in the corpus, and
the honest answer today is "nine static meshes, none of them rigged."
This is Module 2's INSPECT stage of the Aegis pipeline, implemented over
real files rather than described.

Pure stdlib. A .glb is a 12-byte header followed by length-prefixed
chunks; the first chunk is the glTF JSON, which carries everything we
need to report on structure. Binary geometry is only touched to size it.
"""

from __future__ import annotations

import json
import struct
from pathlib import Path

GLB_MAGIC = b"glTF"
CHUNK_JSON = 0x4E4F534A

# What has to be true for a rigging solver to have anything to act on.
RIG_REQUIREMENTS = ("has_mesh", "has_skin", "has_joints")


class AssetError(RuntimeError):
    pass


def parse_glb(path: Path) -> dict:
    data = path.read_bytes()
    if len(data) < 20 or data[:4] != GLB_MAGIC:
        raise AssetError("not a binary glTF (.glb) file")

    version, total = struct.unpack("<II", data[4:12])
    offset, gltf, bin_bytes = 12, None, 0
    while offset + 8 <= len(data):
        chunk_len, chunk_type = struct.unpack("<II", data[offset:offset + 8])
        body = data[offset + 8:offset + 8 + chunk_len]
        if chunk_type == CHUNK_JSON:
            gltf = json.loads(body.decode("utf-8", "replace"))
        else:
            bin_bytes += len(body)
        offset += 8 + chunk_len + (-chunk_len % 4)

    if gltf is None:
        raise AssetError("no glTF JSON chunk found")
    return {"gltf": gltf, "version": version, "declared_bytes": total,
            "binary_bytes": bin_bytes}


def _vertex_count(gltf: dict) -> int:
    accessors = gltf.get("accessors", [])
    total = 0
    for mesh in gltf.get("meshes", []):
        for prim in mesh.get("primitives", []):
            index = prim.get("attributes", {}).get("POSITION")
            if index is not None and index < len(accessors):
                total += accessors[index].get("count", 0)
    return total


def _triangle_count(gltf: dict) -> int:
    accessors = gltf.get("accessors", [])
    total = 0
    for mesh in gltf.get("meshes", []):
        for prim in mesh.get("primitives", []):
            index = prim.get("indices")
            if index is not None and index < len(accessors):
                total += accessors[index].get("count", 0) // 3
    return total


def describe(path: Path, repo_root: Path) -> dict:
    stat = path.stat()
    entry = {
        "name": path.name,
        "path": str(path.relative_to(repo_root)),
        "bytes": stat.st_size,
        "mtime": int(stat.st_mtime),
    }
    try:
        parsed = parse_glb(path)
    except (AssetError, ValueError, struct.error) as error:
        return {**entry, "ok": False, "error": str(error)}

    gltf = parsed["gltf"]
    skins = gltf.get("skins", [])
    joints = sum(len(s.get("joints", [])) for s in skins)
    animations = gltf.get("animations", [])

    # Does this asset have weights already, or would a solver have to
    # generate them? This is the distinction that decides whether the
    # rigging pipeline's job here is validation or synthesis.
    has_weights = any(
        "WEIGHTS_0" in prim.get("attributes", {})
        for mesh in gltf.get("meshes", [])
        for prim in mesh.get("primitives", [])
    )

    facts = {
        "meshes": len(gltf.get("meshes", [])),
        "primitives": sum(len(m.get("primitives", [])) for m in gltf.get("meshes", [])),
        "nodes": len(gltf.get("nodes", [])),
        "materials": len(gltf.get("materials", [])),
        "textures": len(gltf.get("textures", [])),
        "skins": len(skins),
        "joints": joints,
        "animations": len(animations),
        "animation_names": [a.get("name", "(unnamed)") for a in animations][:6],
        "vertices": _vertex_count(gltf),
        "triangles": _triangle_count(gltf),
        "has_weights": has_weights,
        "generator": gltf.get("asset", {}).get("generator", "unknown"),
        "gltf_version": gltf.get("asset", {}).get("version", "?"),
        "binary_bytes": parsed["binary_bytes"],
    }

    checks = {
        "has_mesh": facts["meshes"] > 0,
        "has_skin": facts["skins"] > 0,
        "has_joints": facts["joints"] > 0,
    }
    rigged = all(checks[k] for k in RIG_REQUIREMENTS)

    if rigged:
        state, note = "rigged", "has skeleton and skin bindings"
    elif facts["meshes"] > 0:
        state, note = "static", "geometry present, no skeleton — a solver would synthesise one"
    else:
        state, note = "empty", "no mesh data"

    return {**entry, "ok": True, **facts, "checks": checks,
            "state": state, "note": note}


# --- VALIDATE ---------------------------------------------------------------
# Packet Beta names "weight bleeding across disjoint meshes" as the failure
# mode of proximity-based auto-weighting. Disjointness is the trigger, and it
# is computable: two vertices belong to the same shell iff a path of shared
# triangles connects them. A mesh that looks like one object but is twenty
# unconnected shells is exactly where a proximity solver assigns a hand bone
# to a shirt button.

COMPONENT_FORMATS = {5121: ("B", 1), 5123: ("H", 2), 5125: ("I", 4)}


def _read_indices(gltf: dict, blob: bytes, bin_offset: int, accessor_index: int):
    accessor = gltf["accessors"][accessor_index]
    fmt, size = COMPONENT_FORMATS[accessor["componentType"]]
    view = gltf["bufferViews"][accessor["bufferView"]]
    start = bin_offset + view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
    count = accessor["count"]
    return struct.unpack_from(f"<{count}{fmt}", blob, start)


def _bin_chunk_offset(data: bytes) -> int:
    offset = 12
    while offset + 8 <= len(data):
        chunk_len, chunk_type = struct.unpack("<II", data[offset:offset + 8])
        if chunk_type != CHUNK_JSON:
            return offset + 8
        offset += 8 + chunk_len + (-chunk_len % 4)
    raise AssetError("no binary chunk")


def connected_components(indices, vertex_count: int) -> list[int]:
    """Label every vertex with the shell it belongs to. Union-find with path
    compression; iterative, because a 2M-triangle mesh will not tolerate
    recursion or anything clever.

    Returns a label per vertex, densely numbered from 0. Both VALIDATE (which
    only counts them) and the rigging solver (which weights per shell) read
    shells through this one function, so they cannot disagree about what a
    shell is.
    """
    parent = list(range(vertex_count))

    def find(x: int) -> int:
        root = x
        while parent[root] != root:
            root = parent[root]
        while parent[x] != root:      # path compression
            parent[x], x = root, parent[x]
        return root

    for i in range(0, len(indices) - 2, 3):
        a, b, c = indices[i], indices[i + 1], indices[i + 2]
        ra, rb, rc = find(a), find(b), find(c)
        if ra != rb:
            parent[rb] = ra
            rb = ra
        if ra != rc:
            parent[rc] = ra

    dense: dict[int, int] = {}
    labels = [0] * vertex_count
    for v in range(vertex_count):
        root = find(v)
        label = dense.get(root)
        if label is None:
            label = dense[root] = len(dense)
        labels[v] = label
    return labels


def shell_analysis(path: Path) -> dict:
    """Count connected components per primitive."""
    data = path.read_bytes()
    parsed = parse_glb(path)
    gltf = parsed["gltf"]
    bin_offset = _bin_chunk_offset(data)

    primitives, total_shells, largest_ratio = [], 0, 1.0
    for mesh_index, mesh in enumerate(gltf.get("meshes", [])):
        for prim_index, prim in enumerate(mesh.get("primitives", [])):
            pos = prim.get("attributes", {}).get("POSITION")
            idx = prim.get("indices")
            if pos is None or idx is None:
                continue
            vertex_count = gltf["accessors"][pos]["count"]
            indices = _read_indices(gltf, data, bin_offset, idx)

            labels = connected_components(indices, vertex_count)
            sizes: dict[int, int] = {}
            for label in labels:
                sizes[label] = sizes.get(label, 0) + 1

            ordered = sorted(sizes.values(), reverse=True)
            shells = len(ordered)
            total_shells += shells
            if ordered:
                largest_ratio = min(largest_ratio, ordered[0] / vertex_count)
            primitives.append({
                "mesh": mesh_index, "primitive": prim_index,
                "vertices": vertex_count, "triangles": len(indices) // 3,
                "shells": shells,
                "largest_shell": ordered[0] if ordered else 0,
                "shell_sizes": ordered[:8],
                "orphan_vertices": sum(1 for s in ordered if s == 1),
            })

    # Risk is about how *fragmented* the geometry is, not raw shell count:
    # a two-shell mesh where both halves are large is far less dangerous to
    # auto-weight than one dominant body plus 200 loose fragments.
    if total_shells <= 1:
        risk, note = "low", "single connected shell — proximity weighting has no disjoint gap to bleed across"
    elif total_shells <= 8:
        risk, note = "moderate", f"{total_shells} disjoint shells — weights must be solved per shell, not by global proximity"
    else:
        risk, note = "high", f"{total_shells} disjoint shells — proximity-based auto-weighting will bleed between unconnected parts"

    return {
        "ok": True,
        "primitives": primitives,
        "total_shells": total_shells,
        "largest_shell_ratio": round(largest_ratio, 4),
        "weight_bleed_risk": risk,
        "note": note,
    }


def collect(repo_root: Path) -> dict:
    assets = []
    for path in sorted(repo_root.rglob("*.glb")):
        if "node_modules" in path.parts or ".venv" in path.parts:
            continue
        assets.append(describe(path, repo_root))

    ok = [a for a in assets if a.get("ok")]
    return {
        "assets": assets,
        "summary": {
            "total": len(assets),
            "readable": len(ok),
            "rigged": sum(1 for a in ok if a["state"] == "rigged"),
            "static": sum(1 for a in ok if a["state"] == "static"),
            "vertices": sum(a.get("vertices", 0) for a in ok),
            "triangles": sum(a.get("triangles", 0) for a in ok),
            "bytes": sum(a.get("bytes", 0) for a in assets),
        },
    }
