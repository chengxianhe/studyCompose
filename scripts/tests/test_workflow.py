"""Exercise gate failures and snapshot invalidation in disposable repositories."""

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


SCRIPTS = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("workspace_fingerprint", SCRIPTS / "workspace_fingerprint.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class WorkflowTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        (self.root / "scripts/tests").mkdir(parents=True)
        for name in ("verify.sh", "workspace_fingerprint.py"):
            shutil.copyfile(SCRIPTS / name, self.root / "scripts" / name)
        (self.root / ".gitignore").write_text(".verification/\n__pycache__/\n")
        (self.root / "scripts/tests/test_fixture.py").write_text(
            "import unittest\nclass Fixture(unittest.TestCase):\n    def test_fixture(self):\n        pass\n"
        )
        (self.root / "tracked.txt").write_text("original\n")
        self.git("init", "-q")
        self.git("add", ".")
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "initial")

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True)

    def signature(self):
        return MODULE.fingerprint(self.root)

    def verify(self, mode):
        return subprocess.run(
            ["bash", "scripts/verify.sh", mode], cwd=self.root, text=True, capture_output=True
        )

    def fake_gradle(self, body):
        path = self.root / "gradlew"
        path.write_text("#!/usr/bin/env bash\n" + body)
        path.chmod(0o755)

    def test_snapshot_covers_worktree_index_untracked_deletion_and_head(self):
        signatures = [self.signature()]
        path = self.root / "tracked.txt"
        path.write_text("modified\n")
        signatures.append(self.signature())
        self.git("add", "tracked.txt")
        signatures.append(self.signature())
        extra = self.root / "untracked.txt"
        extra.write_text("new\n")
        signatures.append(self.signature())
        extra.write_text("changed\n")
        signatures.append(self.signature())
        path.unlink()
        signatures.append(self.signature())
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "staged")
        signatures.append(self.signature())
        self.assertEqual(len(signatures), len(set(signatures)))

    def test_ignored_logs_do_not_invalidate_snapshot(self):
        before = self.signature()
        logs = self.root / ".verification"
        logs.mkdir()
        (logs / "result.txt").write_text("passed")
        self.assertEqual(before, self.signature())

    def test_symlink_target_and_executable_bit_invalidate_snapshot(self):
        link = self.root / "link"
        link.symlink_to("tracked.txt")
        before = self.signature()
        link.unlink()
        link.symlink_to("missing.txt")
        self.assertNotEqual(before, self.signature())
        before = self.signature()
        (self.root / "tracked.txt").chmod(0o755)
        self.assertNotEqual(before, self.signature())

    def test_android_runs_all_required_gates_and_records_success(self):
        self.fake_gradle('printf "%s\\n" "$@" > .verification/gradle-args.txt\n')
        result = self.verify("android")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        args = (self.root / ".verification/gradle-args.txt").read_text().splitlines()
        self.assertEqual(
            ["--console=plain", ":konsistTest:test", "detekt", "lint", "test", "spotlessCheck",
             ":app:dependencyGuard", "assembleDebug"], args
        )
        evidence = next((self.root / ".verification").glob("android.*"))
        self.assertEqual("0", (evidence / "exit-code.txt").read_text().strip())
        self.assertEqual(
            (evidence / "fingerprint-before.txt").read_text(),
            (evidence / "fingerprint-after.txt").read_text(),
        )

    def test_gradle_failure_is_not_hidden_by_tee(self):
        self.fake_gradle("echo broken\nexit 17\n")
        result = self.verify("android")
        self.assertEqual(17, result.returncode)
        evidence = next((self.root / ".verification").glob("android.*"))
        self.assertIn("broken", (evidence / "output.log").read_text())

    def test_workspace_mutation_invalidates_successful_run(self):
        self.fake_gradle("echo changed > tracked.txt\n")
        result = self.verify("android")
        self.assertNotEqual(0, result.returncode)
        self.assertIn("Workspace changed", result.stderr)

    def test_diff_failure_stops_before_gradle(self):
        (self.root / "tracked.txt").write_text("trailing whitespace   \n")
        self.fake_gradle("echo called > .verification/called\n")
        self.assertNotEqual(0, self.verify("android").returncode)
        self.assertFalse((self.root / ".verification/called").exists())

    def test_invalid_mode_is_rejected(self):
        self.assertEqual(2, self.verify("unknown").returncode)
        self.assertFalse((self.root / ".verification").exists())

    def test_platform_routes_commands_and_stops_on_failure(self):
        (self.root / "platform").mkdir()
        (self.root / ".mcp.json").write_text(json.dumps({"mcpServers": {}}))
        binary = self.root / "bin"
        binary.mkdir()
        uv = binary / "uv"
        uv.write_text(
            '#!/usr/bin/env bash\nprintf "%s\\n" "$*" >> ../.verification/uv-args.txt\n'
            'if [ "$*" = "run mypy --strict src tests" ]; then exit 9; fi\n'
        )
        uv.chmod(0o755)
        result = subprocess.run(
            ["bash", "scripts/verify.sh", "platform"], cwd=self.root, capture_output=True,
            env={**os.environ, "PATH": str(binary) + os.pathsep + os.environ["PATH"]},
        )
        self.assertEqual(9, result.returncode)
        args = (self.root / ".verification/uv-args.txt").read_text().splitlines()
        self.assertEqual(["sync --locked", "run ruff check .", "run mypy --strict src tests"], args)


if __name__ == "__main__":
    unittest.main()
