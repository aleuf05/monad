#!/usr/bin/env python3
"""Aegis pipeline stages 3-6: AUTHORIZE, EXECUTE, RECORD.

INSPECT says what an asset is. VALIDATE says whether it can be rigged safely.
These three do the rest:

- **AUTHORIZE** runs the gates and issues a token. Nothing is written. This is
  Packet Beta's Module 3 sign-off point, and it exists so that the decision to
  rig is a separate, inspectable act from the rigging.
- **EXECUTE** consumes a token exactly once and writes the rigged asset.
- **RECORD** commits it to git.

RECORD reuses git rather than reimplementing provenance. That question came up
in three packets and is settled here: git already stores content-addressed
history with authorship and timestamps, and the repo's standing rule is one
source of truth per concern rather than a second ledger to keep in sync. A
bespoke provenance store would be a copy of git that can disagree with git.
Packet Beta's Module 4 fields (source hash, joint offsets, weight telemetry)
go into the commit message, where `git log` is the query interface.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "aegis-inspect"))
import inspector  # noqa: E402
import solver  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
RIGGED_DIR = REPO_ROOT / "web/assets/rigged"

# Authorizations live in memory. A restart drops them, which is correct: an
# authorization is a decision about the asset as it is right now, and the
# server cannot vouch for that across its own lifetime.
_AUTHORIZATIONS: dict[str, dict] = {}


class PipelineError(RuntimeError):
    pass


def _rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def _gate(name: str, passed: bool, detail: str) -> dict:
    return {"gate": name, "passed": passed, "detail": detail}


def authorize(source: Path, joint_count: int = solver.DEFAULT_JOINTS) -> dict:
    """Run the gates. Writes nothing; issues a token if every gate passes."""
    facts = inspector.describe(source, REPO_ROOT)
    gates = []

    gates.append(_gate("parses", bool(facts.get("ok")),
                       facts.get("error", "readable binary glTF")))
    if facts.get("ok"):
        gates.append(_gate(
            "has geometry", facts["meshes"] > 0,
            f"{facts['meshes']} mesh, {facts['vertices']:,} vertices"))
        gates.append(_gate(
            "not already rigged", facts["state"] != "rigged",
            "static — a skeleton will be synthesised" if facts["state"] != "rigged"
            else "asset already carries a skin; re-rigging would discard it"))
        gates.append(_gate(
            "single primitive", facts["primitives"] == 1,
            f"{facts['primitives']} primitive"
            + ("" if facts["primitives"] == 1 else " — solver v0.1 handles one")))

    shells = None
    if facts.get("ok") and facts.get("meshes"):
        try:
            shells = inspector.shell_analysis(source)
        except Exception as error:  # noqa: BLE001 - a gate failure, not a crash
            gates.append(_gate("shell analysis", False, str(error)))

    if shells:
        # Not a pass/fail gate — fragmentation is a property of the asset, not
        # a defect. It decides how much of the mesh can deform at all, so it
        # belongs in front of whoever authorizes the run.
        gates.append(_gate("shell analysis", True,
                           f"{shells['total_shells']} disjoint shells, "
                           f"weight-bleed risk {shells['weight_bleed_risk']}"))

    passed = all(g["passed"] for g in gates) and bool(gates)
    dest = RIGGED_DIR / f"{source.stem}-rigged.glb"

    record = {
        "ok": passed,
        "stage": "AUTHORIZE",
        "source": _rel(source),
        "dest": _rel(dest),
        "joint_count": joint_count,
        "gates": gates,
        "facts": facts,
        "shells": shells,
        "engine": "rust" if solver.core_available() else "python",
        "issued_at": int(time.time()),
    }

    if passed:
        token = hashlib.sha256(
            f"{_rel(source)}|{joint_count}|{time.time_ns()}".encode()).hexdigest()[:16]
        record["token"] = token
        record["note"] = "authorized — EXECUTE will write the rigged asset"
        _AUTHORIZATIONS[token] = {**record, "source_path": source, "dest_path": dest,
                                  "consumed": False}
    else:
        failed = [g["gate"] for g in gates if not g["passed"]]
        record["note"] = "not authorized: " + ", ".join(failed)

    return record


def execute(token: str) -> dict:
    """Spend a token and write the rigged asset. One token, one run."""
    auth = _AUTHORIZATIONS.get(token)
    if auth is None:
        raise PipelineError("unknown or expired authorization token")
    if auth["consumed"]:
        raise PipelineError("authorization already spent — AUTHORIZE again to re-run")

    try:
        report = solver.write_rigged(auth["source_path"], auth["dest_path"],
                                     auth["joint_count"])
    except OSError as error:
        raise PipelineError(
            f"cannot write {_rel(auth['dest_path'])}: {error}. The service unit "
            "needs ReadWritePaths for the output directory.") from error

    auth["consumed"] = True
    auth["report"] = report
    report.update({"stage": "EXECUTE", "token": token,
                   "source": _rel(auth["source_path"]),
                   "dest": _rel(auth["dest_path"])})
    return report


def _git(*args: str) -> str:
    result = subprocess.run(["git", "-C", str(REPO_ROOT), *args],
                            capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise PipelineError(f"git {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout.strip()


def record(token: str) -> dict:
    """Commit the rigged asset. Git is the provenance store."""
    auth = _AUTHORIZATIONS.get(token)
    if auth is None:
        raise PipelineError("unknown or expired authorization token")
    report = auth.get("report")
    if report is None:
        raise PipelineError("nothing to record — EXECUTE has not run for this token")
    if auth.get("recorded"):
        raise PipelineError(f"already recorded as {auth['commit']}")

    dest_rel = _rel(auth["dest_path"])
    message = "\n".join([
        f"Aegis RECORD: rig {auth['dest_path'].name}",
        "",
        f"Source: {report['source']}",
        f"Source-SHA256: {report['source_sha256']}",
        f"Rigged-SHA256: {report['rigged_sha256']}",
        f"Vertices: {report['vertices']}",
        f"Joints: {report['joint_count']} ({', '.join(report['joint_names'])})",
        f"Chain-Axis: {report['axis']}  Bone-Span: {report['bone_span']}",
        f"Shells: {report['shells']} "
        f"({report['rigid_shells']} rigid, {report['blended_shells']} blended)",
        f"Rigid-Vertices: {report['rigid_vertices']}  "
        f"Blended-Vertices: {report['blended_vertices']}",
        f"Max-Weight-Error: {report['max_weight_error']}",
        f"Solver-Engine: {report['engine']}  Solve-Ms: {report['solve_ms']}",
        f"Authorization: {token}",
    ])

    _git("add", "--", dest_rel)
    # --only, so a commit triggered from a web button can never sweep up
    # whatever else happens to be in the working tree.
    _git("commit", "--only", "-m", message, "--", dest_rel)
    commit = _git("rev-parse", "HEAD")

    auth["recorded"] = True
    auth["commit"] = commit
    return {
        "ok": True,
        "stage": "RECORD",
        "commit": commit,
        "short": commit[:8],
        "path": dest_rel,
        "message": message,
        "note": "provenance is the commit — git log is the query interface",
    }


def status(token: str) -> dict:
    auth = _AUTHORIZATIONS.get(token)
    if auth is None:
        return {"ok": False, "error": "unknown token"}
    return {
        "ok": True,
        "token": token,
        "authorized": True,
        "executed": auth["consumed"],
        "recorded": bool(auth.get("recorded")),
        "commit": auth.get("commit"),
    }
