"""Portable argument/environment contracts; real UID tests run in Docker CI."""

import importlib.util
import io
import stat
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / "agents" / "base" / "model-execution.py"
SPEC = importlib.util.spec_from_file_location("model_execution", SOURCE)
MODEL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODEL)


class ModelExecutionTests(unittest.TestCase):
    def run_model(self, timeout=30, check_result=0):
        calls = []

        def execute(command, repo, environment, deadline):
            calls.append((command, repo, dict(environment), deadline))
            return check_result if len(calls) == 1 else 0

        info = SimpleNamespace(st_mode=stat.S_IFDIR | 0o700, st_uid=10001)
        with (
            patch.object(MODEL, "protected_parent"),
            patch.object(Path, "lstat", return_value=info),
            patch.object(MODEL, "execute", side_effect=execute),
            patch.object(
                MODEL.sys, "stdin", io.StringIO("fixture-provider\n@ripley task")
            ),
            patch.dict(
                MODEL.os.environ,
                {
                    "GITHUB_TOKEN": "DUMMY_APP",
                    "IDENTITY_HEADER": "DUMMY_MI",
                    "PATH": "model-controlled",
                    "PYTHONPATH": "model-controlled",
                },
            ),
        ):
            result = MODEL.run(Path("candidate"), Path("home"), timeout)
        return result, calls

    def test_only_cli_gets_provider_and_no_controller_environment(self):
        result, calls = self.run_model()
        self.assertEqual(result, 0)
        self.assertEqual(len(calls), 2)
        self.assertNotIn("COPILOT_GITHUB_TOKEN", calls[0][2])
        self.assertEqual(calls[1][2]["COPILOT_GITHUB_TOKEN"], "fixture-provider")
        self.assertEqual(calls[1][2]["PATH"], MODEL.MODEL_PATH)
        for _, _, environment, _ in calls:
            for name in ("GITHUB_TOKEN", "GH_TOKEN", "IDENTITY_HEADER", "PYTHONPATH"):
                self.assertNotIn(name, environment)
        self.assertNotIn("fixture-provider", " ".join(calls[1][0]))
        self.assertEqual(calls[1][0][0], "/usr/local/bin/copilot")
        self.assertIn("--agent", calls[1][0])
        self.assertIn("Squad", calls[1][0])
        self.assertIn(
            "--secret-env-vars=COPILOT_GITHUB_TOKEN,IDENTITY_HEADER,MSI_SECRET",
            calls[1][0],
        )

    def test_profile_failure_never_receives_provider_or_runs_cli(self):
        result, calls = self.run_model(check_result=1)
        self.assertEqual(result, 1)
        self.assertEqual(len(calls), 1)
        self.assertNotIn("COPILOT_GITHUB_TOKEN", calls[0][2])

    def test_unbounded_deadline_cannot_launch(self):
        with self.assertRaises(ValueError):
            self.run_model(timeout=481)

    def test_privilege_drop_has_fixed_uid_no_groups_or_capabilities(self):
        self.assertEqual(MODEL.DROP_PRIVILEGES[0], "/usr/bin/setpriv")
        for flag in (
            "--reuid=10001",
            "--regid=10001",
            "--clear-groups",
            "--no-new-privs",
            "--inh-caps=-all",
            "--ambient-caps=-all",
            "--bounding-set=-all",
        ):
            self.assertIn(flag, MODEL.DROP_PRIVILEGES)

    def test_unprivileged_caller_cannot_launch_controller_helper(self):
        with (
            patch.object(MODEL.os, "geteuid", return_value=10001, create=True),
            self.assertRaises(ValueError),
        ):
            MODEL.main()
