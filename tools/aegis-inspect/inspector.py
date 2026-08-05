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
