#!/usr/bin/env python3
"""Fixed-scope Git path for explicitly authorized Rocket Notebook publication."""
from pathlib import Path
import json
import subprocess
import sys

ROOT = Path("/home/cgl/dev/rocketry").resolve()
EXPECTED_ORIGIN = "https://github.com/mds2/rocketry.git"


def git(*args, timeout=120):
    return subprocess.run(["git", "-C", str(ROOT), *args], text=True,
                          capture_output=True, timeout=timeout, check=False)


def fail(message):
    print(json.dumps({"ok": False, "error": message}))
    raise SystemExit(1)


if len(sys.argv) != 2 or sys.argv[1] != "commit-readme-push":
    fail("unsupported Git action")
if not ROOT.is_dir() or not (ROOT / ".git").is_dir():
    fail("verified Rocket Notebook repository is unavailable")
if (ROOT / ".git" / "index.lock").exists():
    fail("Git index lock already exists; no lock was removed")

branch = git("branch", "--show-current")
origin = git("remote", "get-url", "origin")
if branch.returncode != 0 or branch.stdout.strip() != "main":
    fail("refusing publication outside main")
if origin.returncode != 0 or origin.stdout.strip() != EXPECTED_ORIGIN:
    fail("refusing publication to an unverified origin")

check = git("diff", "--check")
if check.returncode != 0:
    fail("README diff has whitespace errors")
status = git("status", "--porcelain")
lines = [line for line in status.stdout.splitlines() if line]
if lines != [" M README.md"]:
    fail("refusing publication because unrelated changes are present")

added = git("add", "--", "README.md")
if added.returncode != 0:
    fail("Git could not stage README.md")
cached = git("diff", "--cached", "--quiet", "--", "README.md")
if cached.returncode == 0:
    fail("README.md has no staged changes")
if cached.returncode != 1:
    fail("could not inspect staged README.md")

commit = git("commit", "-m", "Update Rocket Notebook README")
if commit.returncode != 0:
    fail("Git commit failed: " + commit.stderr.strip()[:400])
commit_id = git("rev-parse", "HEAD").stdout.strip()

push = git("push", "origin", "main")
result = {
    "ok": push.returncode == 0,
    "commit": commit_id,
    "push_output": (push.stdout + push.stderr).strip()[:800],
}
if push.returncode != 0:
    result["error"] = "push failed; commit was created and was not retried"
print(json.dumps(result))
raise SystemExit(0 if push.returncode == 0 else 1)
