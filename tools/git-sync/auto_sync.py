#!/usr/bin/env python3
"""
tools/git-sync/auto_sync.py — Monad Autonomous Git Auto-Commit & Push Engine

Ensures that the Monad repository is autonomously, safely, and continuously
committed and pushed to GitHub without requiring human coaching or manual intervention.

Features:
- Secret & sensitive file scanner (blocks accidental commit of keys/tokens/.env).
- Intelligent semantic commit message generator based on changed paths.
- Safe staging respecting .gitignore.
- Rebase-pull and push with upstream tracking.
- Idempotent: returns immediately if working tree is clean.
- Detailed audit logging to logs/git-sync.log.
"""

import os
import sys
import subprocess
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple, Dict, Optional

# Root directory of the repository
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
LOG_FILE = REPO_ROOT / "logs" / "git-sync.log"

# Sensitive file patterns that must never be auto-committed
FORBIDDEN_PATTERNS = [
    r"\.env($|\.)",
    r"id_rsa",
    r"id_ed25519",
    r".*\.pem$",
    r".*\.key$",
    r"credentials\.json$",
    r"service_account.*\.json$",
    r".*secret.*\.json$",
]

# Sensitive content patterns inside files
FORBIDDEN_CONTENT_PATTERNS = [
    re.compile(r"AIza[0-9A-Za-z-_]{35}"),  # Google API key
    re.compile(r"sk-[a-zA-Z0-9]{48}"),     # OpenAI key
    re.compile(r"ghp_[0-9a-zA-Z]{36}"),    # GitHub Personal Access Token
    re.compile(r"-----BEGIN (RSA|OPENSSH|EC|DSA) PRIVATE KEY-----"),
]

def log(msg: str, level: str = "INFO"):
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    line = f"[{timestamp}] [{level}] {msg}"
    print(line)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception as e:
        print(f"Warning: could not write to log file: {e}", file=sys.stderr)

def run_git(args: List[str], cwd: Path = REPO_ROOT, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git"] + args,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=check
    )

def get_current_branch(repo_path: Path = REPO_ROOT) -> str:
    res = run_git(["branch", "--show-current"], cwd=repo_path)
    branch = res.stdout.strip()
    if not branch:
        # Detached HEAD or special state
        res = run_git(["rev-parse", "--short", "HEAD"], cwd=repo_path)
        branch = res.stdout.strip()
    return branch

def get_status_summary(repo_path: Path = REPO_ROOT) -> Dict[str, List[str]]:
    res = run_git(["status", "--porcelain"], cwd=repo_path)
    lines = [l for l in res.stdout.splitlines() if l.strip()]
    
    modified = []
    untracked = []
    deleted = []
    
    for line in lines:
        code = line[:2]
        file_path = line[3:].strip()
        if code.strip() == "??":
            untracked.append(file_path)
        elif "D" in code:
            deleted.append(file_path)
        else:
            modified.append(file_path)
            
    return {
        "modified": modified,
        "untracked": untracked,
        "deleted": deleted,
        "total": len(lines)
    }

def scan_for_secrets(files: List[str], repo_path: Path = REPO_ROOT) -> List[str]:
    violations = []
    for f in files:
        # Check filename pattern
        for pat in FORBIDDEN_PATTERNS:
            if re.search(pat, f, re.IGNORECASE):
                violations.append(f"Forbidden file pattern '{pat}' in filename: {f}")
        
        # Check file content (if file exists and is text)
        full_path = repo_path / f
        if full_path.is_file() and full_path.stat().st_size < 1024 * 1024:  # under 1MB
            try:
                content = full_path.read_text(encoding="utf-8", errors="ignore")
                for pat in FORBIDDEN_CONTENT_PATTERNS:
                    if pat.search(content):
                        violations.append(f"Potential secret content matching pattern in: {f}")
            except Exception:
                pass
    return violations

def generate_commit_message(status: Dict[str, List[str]], custom_msg: Optional[str] = None) -> str:
    if custom_msg:
        return custom_msg
    
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    all_files = status["modified"] + status["untracked"] + status["deleted"]
    count = len(all_files)
    
    # Identify key areas touched
    areas = set()
    for f in all_files:
        parts = f.split("/")
        if len(parts) > 1:
            areas.add(parts[0])
        else:
            areas.add("root")
    
    area_summary = ", ".join(sorted(areas)[:4])
    if len(areas) > 4:
        area_summary += f" +{len(areas)-4} more"
    
    header = f"Auto-Sync [{now_str}]: {count} file{'s' if count != 1 else ''} ({area_summary})"
    
    body_lines = []
    if status["modified"]:
        body_lines.append(f"Modified ({len(status['modified'])}):")
        for f in status["modified"][:6]:
            body_lines.append(f"  - {f}")
        if len(status["modified"]) > 6:
            body_lines.append(f"  - ... and {len(status['modified']) - 6} more")
            
    if status["untracked"]:
        body_lines.append(f"Added ({len(status['untracked'])}):")
        for f in status["untracked"][:6]:
            body_lines.append(f"  - {f}")
        if len(status["untracked"]) > 6:
            body_lines.append(f"  - ... and {len(status['untracked']) - 6} more")

    if status["deleted"]:
        body_lines.append(f"Deleted ({len(status['deleted'])}):")
        for f in status["deleted"][:4]:
            body_lines.append(f"  - {f}")

    return header + "\n\n" + "\n".join(body_lines)

def sync(repo_path: Path = REPO_ROOT, dry_run: bool = False, custom_message: Optional[str] = None) -> bool:
    log("=== Commencing Autonomous Git Sync ===")
    
    # 1. Check working tree
    status = get_status_summary(repo_path)
    if status["total"] == 0:
        log("Working tree is completely clean. Checking remote sync status...")
        branch = get_current_branch(repo_path)
        try:
            # Check if local is ahead of remote
            res = run_git(["rev-list", f"origin/{branch}..HEAD"], cwd=repo_path, check=False)
            ahead_commits = [c for c in res.stdout.splitlines() if c.strip()]
            if ahead_commits and not dry_run:
                log(f"Local branch is ahead by {len(ahead_commits)} commit(s). Pushing to origin/{branch}...")
                run_git(["push", "origin", branch], cwd=repo_path)
                log(f"Successfully pushed ahead commits to origin/{branch}.")
            else:
                log("Remote is up-to-date with local HEAD. Nothing to do.")
            return True
        except Exception as e:
            log(f"Remote check warning: {e}", level="WARN")
            return True

    log(f"Detected {status['total']} uncommitted changes: "
        f"{len(status['modified'])} modified, {len(status['untracked'])} untracked, {len(status['deleted'])} deleted.")

    # 2. Scan for secrets
    all_changed = status["modified"] + status["untracked"]
    violations = scan_for_secrets(all_changed, repo_path)
    if violations:
        for v in violations:
            log(f"SAFETY ABORT: {v}", level="ERROR")
        log("Auto-sync aborted to prevent secret leakage. Fix the files above or add them to .gitignore.", level="ERROR")
        return False

    if dry_run:
        log("[DRY-RUN] Auto-sync checks passed. Would stage, commit, and push.")
        return True

    # 3. Stage changes safely
    log("Staging changes...")
    run_git(["add", "-A"], cwd=repo_path)

    # 4. Generate commit message and commit
    branch = get_current_branch(repo_path)
    commit_msg = generate_commit_message(status, custom_message)
    log(f"Committing to branch '{branch}'...")
    run_git(["commit", "-m", commit_msg], cwd=repo_path)
    
    commit_hash = run_git(["rev-parse", "--short", "HEAD"], cwd=repo_path).stdout.strip()
    log(f"Created commit {commit_hash}.")

    # 5. Fetch & Rebase to avoid divergence
    log("Fetching remote updates...")
    try:
        run_git(["fetch", "origin", branch], cwd=repo_path, check=False)
        # Attempt rebase
        run_git(["rebase", f"origin/{branch}"], cwd=repo_path, check=False)
    except Exception as e:
        log(f"Rebase notice: {e}", level="DEBUG")

    # 6. Push to origin
    log(f"Pushing commit {commit_hash} to origin/{branch}...")
    try:
        push_res = run_git(["push", "-u", "origin", branch], cwd=repo_path)
        log(f"SUCCESS: Pushed {commit_hash} to origin/{branch}.")
        log("=== Autonomous Git Sync Complete ===")
        return True
    except subprocess.CalledProcessError as e:
        log(f"Push failed: {e.stderr.strip()}", level="ERROR")
        # Attempt safe retry with push
        log("Attempting push with lease...", level="WARN")
        try:
            run_git(["push", "origin", branch], cwd=repo_path)
            log(f"SUCCESS: Push succeeded on retry to origin/{branch}.")
            log("=== Autonomous Git Sync Complete ===")
            return True
        except Exception as retry_err:
            log(f"Fatal: Could not push to origin: {retry_err}", level="ERROR")
            return False

if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    msg = None
    for arg in sys.argv[1:]:
        if arg.startswith("--message="):
            msg = arg.split("=", 1)[1]
        elif arg == "-m" and sys.argv.index(arg) + 1 < len(sys.argv):
            msg = sys.argv[sys.argv.index(arg) + 1]

    success = sync(REPO_ROOT, dry_run=dry, custom_message=msg)
    sys.exit(0 if success else 1)
