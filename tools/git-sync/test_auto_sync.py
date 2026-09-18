#!/usr/bin/env python3
"""
tools/git-sync/test_auto_sync.py — Unit Tests for Autonomous Git Sync Engine
"""

import os
import sys
import shutil
import tempfile
import unittest
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add current directory to sys.path to import auto_sync
sys.path.insert(0, str(Path(__file__).resolve().parent))
from auto_sync import (
    get_status_summary,
    scan_for_secrets,
    generate_commit_message,
    filter_leased_status,
    load_active_lease,
    path_is_leased,
    sync,
    run_git
)

class TestAutoSync(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.repo_path = Path(self.test_dir) / "test_repo"
        self.repo_path.mkdir()
        
        # Initialize test git repo
        subprocess.run(["git", "init", "-b", "main"], cwd=self.repo_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test Captain"], cwd=self.repo_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "captain@monad.local"], cwd=self.repo_path, check=True, capture_output=True)
        
        # Initial commit
        readme = self.repo_path / "README.md"
        readme.write_text("# Test Repo\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=self.repo_path, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=self.repo_path, check=True, capture_output=True)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_clean_status(self):
        status = get_status_summary(self.repo_path)
        self.assertEqual(status["total"], 0)
        self.assertEqual(status["modified"], [])
        self.assertEqual(status["untracked"], [])

    def test_dirty_status_detection(self):
        # Create a new file and edit existing
        new_file = self.repo_path / "test.py"
        new_file.write_text("print('hello')", encoding="utf-8")
        
        readme = self.repo_path / "README.md"
        readme.write_text("# Test Repo Updated\n", encoding="utf-8")
        
        status = get_status_summary(self.repo_path)
        self.assertEqual(status["total"], 2)
        self.assertIn("README.md", status["modified"])
        self.assertIn("test.py", status["untracked"])

    def test_secret_scanner_blocks_env(self):
        env_file = self.repo_path / ".env"
        env_file.write_text("SECRET_KEY=12345", encoding="utf-8")
        violations = scan_for_secrets([".env"], self.repo_path)
        self.assertTrue(len(violations) > 0)
        self.assertIn("Forbidden file pattern", violations[0])

    def test_secret_scanner_blocks_key_content(self):
        key_file = self.repo_path / "config.json"
        mock_token = "ghp_" + ("x" * 36)
        key_file.write_text(f'{{"token": "{mock_token}"}}', encoding="utf-8")
        violations = scan_for_secrets(["config.json"], self.repo_path)
        self.assertTrue(len(violations) > 0)
        self.assertIn("secret content", violations[0])

    def test_commit_message_generation(self):
        status = {
            "modified": ["web/index.html", "docs/doctrine.md"],
            "untracked": ["tools/new_tool.py"],
            "deleted": [],
            "total": 3
        }
        msg = generate_commit_message(status)
        self.assertIn("Auto-Sync", msg)
        self.assertIn("3 files", msg)
        self.assertIn("web/index.html", msg)
        self.assertIn("tools/new_tool.py", msg)

    def test_dry_run_sync(self):
        new_file = self.repo_path / "test_doc.md"
        new_file.write_text("Durable content", encoding="utf-8")
        
        result = sync(self.repo_path, dry_run=True)
        self.assertTrue(result)
        
        # File should remain untracked in dry run
        status = get_status_summary(self.repo_path)
        self.assertEqual(status["total"], 1)

    def test_lease_holds_only_its_scoped_paths(self):
        status = {
            "modified": ["console/captains-eye.html", "web/data/fleet-status.json"],
            "untracked": ["tools/root-console/new.py"],
            "deleted": ["console/old.html"],
            "total": 4,
        }
        lease = {"paths": ["console", "tools/root-console"], "expires_at": datetime.now(timezone.utc) + timedelta(minutes=1)}
        eligible, held = filter_leased_status(status, lease)
        self.assertEqual(eligible["modified"], ["web/data/fleet-status.json"])
        self.assertEqual(eligible["total"], 1)
        self.assertEqual(set(held), {"console/captains-eye.html", "console/old.html", "tools/root-console/new.py"})
        self.assertTrue(path_is_leased("console/a.html", lease))
        self.assertFalse(path_is_leased("console-tools/a.html", lease))

    def test_expired_lease_is_ignored(self):
        lease_file = Path(self.test_dir) / "lease.json"
        lease_file.write_text('{"paths": ["web"], "expires_at": "2000-01-01T00:00:00Z"}', encoding="utf-8")
        self.assertIsNone(load_active_lease(lease_file))

if __name__ == "__main__":
    unittest.main()
