"""Credential-free probes of the actual controller shell functions."""

import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(os.environ.get("CREDENTIAL_HANDOFF_SOURCE", ROOT / "agents" / "base"))
BASH = r"C:\Program Files\Git\bin\bash.exe" if os.name == "nt" else shutil.which("bash")
APP_TOKEN = "DUMMY_APP_TOKEN_NOT_A_REAL_CREDENTIAL"
COPILOT_TOKEN = "DUMMY_COPILOT_TOKEN_NOT_A_REAL_CREDENTIAL"


def shell_path(path):
    value = Path(path).resolve().as_posix()
    return f"/{value[0].lower()}{value[2:]}" if os.name == "nt" else value


class CredentialHandoffTests(unittest.TestCase):
    def probe(self, operation, *, setup="", extra_environment=None, expected_exit=0,
              fail_environment_reader=False):
        with tempfile.TemporaryDirectory(prefix="credential-handoff-", dir=ROOT / "tests") as folder:
            folder = Path(folder)
            binary = folder / "bin"
            binary.mkdir()
            home = folder / "controlled-home"
            home.mkdir()
            argv_log = folder / "argv"
            environment_log = folder / "environment"
            for executable in ("git", "gh", "python3"):
                script = binary / executable
                script.write_text(
                    "#!/usr/bin/env bash\n"
                    f"printf 'ARG:%s\\n' \"$@\" >> {shlex.quote(shell_path(argv_log))}\n"
                    f"printf 'GH:%s\\nGITHUB:%s\\nCOPILOT:%s\\nUNRELATED:%s\\n' "
                    '"${GH_TOKEN:-}" "${GITHUB_TOKEN:-}" "${COPILOT_TOKEN:-}" '
                    '"${UNRELATED_PRIVATE_SETTING:-}" > '
                    f"{shlex.quote(shell_path(environment_log))}\n"
                    f"/usr/bin/printenv INVALID-NAME >> {shlex.quote(shell_path(environment_log))} || :\n",
                    encoding="utf-8", newline="\n",
                )
                script.chmod(0o755)
            if fail_environment_reader:
                reader = binary / "env"
                reader.write_text("#!/bin/bash\nexit 37\n", encoding="utf-8", newline="\n")
                reader.chmod(0o755)
            runtime = shlex.quote(shell_path(SOURCE / "runtime-contract.sh"))
            entry = (SOURCE / "entrypoint.sh").read_text(encoding="utf-8")
            match = re.search(r"gh\(\) [({]\n.*?\n[})]", entry, flags=re.S)
            self.assertIsNotNone(match)
            command = (
                f"source {runtime}; die() {{ exit 96; }}; "
                f"PATH={shlex.quote(shell_path(binary))}:$PATH; "
                f"TRUSTED_HOME={shlex.quote(shell_path(home))}; "
                "PUBLICATION_HELPER=/synthetic-protected-publication.py; "
                f"GITHUB_TOKEN={shlex.quote(APP_TOKEN)}; "
                f"COPILOT_TOKEN={shlex.quote(COPILOT_TOKEN)}; "
                "export GITHUB_TOKEN COPILOT_TOKEN; "
                f"env() {{ printf 'ENVARG:%s\\n' \"$@\" >> "
                f"{shlex.quote(shell_path(argv_log))}; command env \"$@\"; }}; "
                f"{match.group(0)}; "
                f"{setup}"
                f"{operation}"
            )
            environment = {
                name: value for name, value in os.environ.items()
                if os.name != "nt" or re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name)
            }
            for name in ("GH_TOKEN", "GITHUB_TOKEN", "COPILOT_GITHUB_TOKEN", "COPILOT_TOKEN"):
                environment.pop(name, None)
            environment["UNRELATED_PRIVATE_SETTING"] = "DUMMY_UNRELATED_SETTING"
            environment.update(extra_environment or {})
            result = subprocess.run(
                [BASH, "-c", command], cwd=folder, env=environment,
                capture_output=True, text=True, timeout=15, check=False,
            )
            self.assertEqual(result.returncode, expected_exit, result.stderr)
            if expected_exit:
                self.assertFalse(argv_log.exists(), "An unsafe environment reached a child command")
                self.assertNotIn(APP_TOKEN, result.stderr)
                self.assertNotIn(COPILOT_TOKEN, result.stderr)
                return ""
            argv = argv_log.read_text(encoding="utf-8")
            self.assertNotIn(APP_TOKEN, argv)
            self.assertNotIn(COPILOT_TOKEN, argv)
            actual_environment = environment_log.read_text(encoding="utf-8")
            self.assertNotIn("DUMMY_UNRELATED_SETTING", actual_environment)
            return actual_environment

    def test_trusted_git_uses_environment_not_secret_arguments(self):
        result = self.probe("trusted_git --version")
        self.assertIn(f"GH:{APP_TOKEN}", result)
        self.assertIn("GITHUB:\nCOPILOT:\n", result)

    def test_github_client_uses_environment_not_secret_arguments(self):
        result = self.probe("gh api repos/synthetic/target")
        self.assertIn(f"GH:{APP_TOKEN}", result)
        self.assertIn("GITHUB:\nCOPILOT:\n", result)

    def test_publication_helper_uses_environment_not_secret_arguments(self):
        result = self.probe("publication_python synthetic-check")
        self.assertIn(f"GITHUB:{APP_TOKEN}", result)
        self.assertIn(f"COPILOT:{COPILOT_TOKEN}", result)
        self.assertIn("GH:\n", result)

    def test_exported_readonly_environment_fails_closed(self):
        self.probe(
            "trusted_git --version",
            setup="export READONLY_PRIVATE_SETTING=synthetic; readonly READONLY_PRIVATE_SETTING; ",
            expected_exit=96,
        )

    def test_non_shell_environment_name_fails_closed(self):
        self.probe(
            "trusted_git --version",
            extra_environment={"INVALID-NAME": "DUMMY_INVALID_PRIVATE_SETTING"},
            expected_exit=96,
        )

    def test_failed_environment_reader_cannot_launch_child(self):
        self.probe(
            "trusted_git --version",
            fail_environment_reader=True,
            expected_exit=96,
        )


if __name__ == "__main__":
    unittest.main()
