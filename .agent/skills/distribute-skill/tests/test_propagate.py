import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))
import propagate


class PropagateTest(unittest.TestCase):
    def git(self, repo, *args):
        return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()

    def repo(self):
        path = pathlib.Path(tempfile.mkdtemp(prefix="propagate-test-"))
        self.git(path, "init", "-q")
        self.git(path, "config", "user.email", "test@example.com")
        self.git(path, "config", "user.name", "test")
        (path / "file.txt").write_text("ok\n")
        self.git(path, "add", ".")
        self.git(path, "commit", "-qm", "initial")
        return path

    def test_policy_is_explicit_and_branch_aware(self):
        self.assertEqual(propagate.POLICIES["vettedai"]["integration"], "lovable-staging")
        self.assertEqual(propagate.POLICIES["congrats"]["mode"], "pr")
        self.assertEqual(propagate.POLICIES["backend"]["integration"], "backend-verify-deployment")

    def test_dirty_consumer_is_reported_without_mutation(self):
        repo = self.repo()
        (repo / "local.txt").write_text("keep me\n")
        before = (repo / "local.txt").read_text()
        result = propagate.inspect_consumer("test", {"path": str(repo), "integration": "main", "mode": "direct"})
        self.assertEqual(result["status"], "dirty")
        self.assertEqual((repo / "local.txt").read_text(), before)

    def test_clean_consumer_reports_pointer_only_plan(self):
        repo = self.repo()
        result = propagate.inspect_consumer("test", {"path": str(repo), "integration": "main", "mode": "direct"})
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["action"], "direct")
        self.assertIn("old_pointer", result)


if __name__ == "__main__":
    unittest.main()
