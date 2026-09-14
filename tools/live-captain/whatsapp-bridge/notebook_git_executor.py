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


if len(sys.argv) != 2 or sys.argv[1] not in {"commit-readme-push", "publish-readme-fork-pr"}:
    fail("unsupported Git action")
if not ROOT.is_dir() or not (ROOT / ".git").is_dir():
    fail("verified Rocket Notebook repository is unavailable")
if (ROOT / ".git" / "index.lock").exists():
    fail("Git index lock already exists; no lock was removed")

if sys.argv[1] == "publish-readme-fork-pr":
    BRANCH = "captain/readme-8f594f1"
    COMMIT = "8f594f1fd4cd77c7c0a6172a3f21b4b80bc2a70f"
    EXPECTED_FORK = "git@github.com:aleuf05/rocketry.git"
    fetched = git("fetch", "origin", "main")
    if fetched.returncode != 0:
        fail("could not fetch origin main")
    fork = git("remote", "get-url", "fork")
    if fork.returncode != 0 or fork.stdout.strip() != EXPECTED_FORK:
        fail("refusing publication to an unverified fork")
    if git("cat-file", "-e", "origin/main:README.md").returncode != 0:
        fail("origin/main has no README.md; a section-only PR cannot be isolated without broader changes")
    names = git("diff", "--name-only", f"origin/main...{COMMIT}")
    changed = [line for line in names.stdout.splitlines() if line]
    if changed != ["README.md"]:
        fail("refusing fork PR: proposed diff against origin/main is broader than README.md")
    patch = git("diff", "--unified=0", "--no-color", f"origin/main...{COMMIT}", "--", "README.md")
    if patch.returncode != 0 or "\n+## Captain connection\n" not in patch.stdout or "\n+Authorized work on the Rocket Notebook can be requested through WhatsApp.\n" not in patch.stdout:
        fail("refusing fork PR: README diff is not the authorized Captain connection section")
    if git("diff", "--check", f"origin/main...{COMMIT}", "--", "README.md").returncode != 0:
        fail("refusing fork PR: README diff has whitespace errors")
    if git("show-ref", "--verify", "--quiet", f"refs/heads/{BRANCH}").returncode == 0:
        fail("publication branch already exists locally; no branch was altered")
    remote_branch = git("ls-remote", "--exit-code", "fork", f"refs/heads/{BRANCH}")
    if remote_branch.returncode == 0:
        fail("publication branch already exists on fork; no force push performed")
    created = git("branch", BRANCH, COMMIT)
    if created.returncode != 0:
        fail("could not create isolated publication branch")
    pushed = git("push", "fork", BRANCH)
    if pushed.returncode != 0:
        fail("fork branch push failed; no retry or force push performed")
    pr = subprocess.run([
        "gh", "pr", "create", "--repo", "mds2/rocketry", "--base", "main",
        "--head", "aleuf05:" + BRANCH, "--title", "Add Captain connection note to Rocket Notebook README",
        "--body", "Authorized README-only Rocket Notebook Captain connection note.",
    ], text=True, capture_output=True, timeout=120, check=False)
    if pr.returncode != 0:
        fail("fork branch pushed but PR creation failed: " + (pr.stderr or pr.stdout).strip()[:400])
    print(json.dumps({"ok": True, "mode": "fork-pr", "commit": COMMIT, "branch": BRANCH, "pr": pr.stdout.strip()}))
    raise SystemExit(0)

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
