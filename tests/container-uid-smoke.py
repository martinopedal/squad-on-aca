"""Real-image Linux privilege boundary; no authentication or network operations."""

import base64
import hashlib
import importlib.util
import json
import os
import shlex
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path("/workspace/uid-tests")
PROTECTED = [
    Path(name)
    for name in (
        "/entrypoint.sh",
        "/github-app.sh",
        "/runtime-contract.sh",
        "/readme-publication.py",
        "/model-execution.py",
        "/model-profile.sh",
    )
]
BOT = "fixture-app[bot]"
EMAIL = "789+fixture-app[bot]@users.noreply.github.com"


def git(repo, *args):
    environment = {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": str(ROOT),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "LC_ALL": "C",
    }
    return subprocess.run(
        [
            "git",
            "-c",
            "core.hooksPath=/dev/null",
            "-c",
            "commit.gpgsign=false",
            "-C",
            str(repo),
            *args,
        ],
        env=environment,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


class LinuxBoundary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert os.geteuid() == 0
        cls.copilot = Path("/usr/local/bin/copilot")
        cls.loader = os.readlink(cls.copilot)
        cls.copilot.unlink()
        cls.copilot.write_text(
            '#!/bin/sh\nexec /usr/bin/python3 -I /ci/tests/model-uid-probe.py "$@"\n'
        )
        cls.copilot.chmod(0o555)

    @classmethod
    def tearDownClass(cls):
        cls.copilot.unlink()
        cls.copilot.symlink_to(cls.loader)
        shutil.rmtree(ROOT)

    def setUp(self):
        if ROOT.exists():
            shutil.rmtree(ROOT)
        ROOT.mkdir(mode=0o755)
        self.repo = ROOT / "repo"
        self.home = ROOT / "model-home"
        self.publisher = ROOT / "publisher"
        self.publisher.mkdir(mode=0o700)
        self.trusted_home = ROOT / "trusted-home"
        self.trusted_home.mkdir(mode=0o700)
        secret = ROOT / "root-secret"
        secret.write_text("DUMMY_ROOT_CREDENTIAL\n")
        secret.chmod(0o600)
        self.controller = subprocess.Popen(
            ["/bin/sleep", "90"],
            env={"DUMMY_ROOT_MARKER": "DUMMY_ROOT_CREDENTIAL"},
        )
        self.hashes = {
            str(path): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in PROTECTED
        }
        origin = ROOT / "origin"
        origin.mkdir()
        git(origin, "init", "-q", "-b", "main", "--template=")
        git(origin, "config", "user.name", BOT)
        git(origin, "config", "user.email", EMAIL)
        (origin / "README.md").write_text("# Synthetic native Squad fixture\n")
        (origin / ".github" / "agents").mkdir(parents=True)
        (origin / ".github" / "agents" / "squad.agent.md").write_text(
            "---\nname: Squad\n---\n"
        )
        (origin / ".squad").mkdir()
        (origin / ".squad" / "team.md").write_text("Synthetic tracked ripley team\n")
        (origin / "scripts").mkdir()
        (origin / "scripts" / "check-hosted-squad-setup.mjs").write_text(
            "if (process.getuid() !== 10001 || process.env.COPILOT_GITHUB_TOKEN "
            "|| process.env.GITHUB_TOKEN) process.exit(1);\n"
        )
        git(origin, "add", ".")
        git(origin, "commit", "-qm", "Synthetic qualified main")
        self.base = git(origin, "rev-parse", "HEAD")
        git(ROOT, "clone", "-q", "--no-local", str(origin), str(self.repo))
        git(self.repo, "config", "user.name", BOT)
        git(self.repo, "config", "user.email", EMAIL)
        git(self.publisher, "init", "-q", "--template=")
        git(self.publisher, "fetch", "-q", str(origin), "main")

    def tearDown(self):
        self.controller.terminate()
        self.controller.wait(timeout=5)

    def context(self, mode):
        (ROOT / "probe-context.json").write_text(
            json.dumps(
                {
                    "mode": mode,
                    "controller": self.controller.pid,
                }
            )
        )

    def model(self, mode="protected"):
        self.context(mode)
        subprocess.run(
            [
                "/usr/bin/python3",
                "-I",
                "/model-execution.py",
                "prepare",
                str(self.repo),
                str(self.home),
            ],
            check=True,
            capture_output=True,
        )
        # Intentionally hostile controller environment must not reach native code.
        environment = dict(
            os.environ,
            GITHUB_TOKEN="fixture-app-secret",
            GH_TOKEN="fixture-app-secret",
            IDENTITY_HEADER="DUMMY_MI_HEADER",
            COPILOT_TOKEN="fixture-copilot-secret",
            PYTHONPATH=str(self.repo / ".git"),
            BASH_ENV=str(self.repo / ".git" / "model-hook"),
            DUMMY_ROOT_MARKER="DUMMY_ROOT_CREDENTIAL",
        )
        return subprocess.run(
            [
                "/usr/bin/python3",
                "-I",
                "/model-execution.py",
                "run",
                str(self.repo),
                str(self.home),
                "30",
            ],
            input="fixture-copilot-secret\n@ripley, change only README.md.",
            env=environment,
            capture_output=True,
            text=True,
            timeout=40,
            check=False,
        )

    def unchanged(self):
        for path in PROTECTED:
            self.assertEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(), self.hashes[str(path)]
            )
            for parent in (path, *path.parents):
                self.assertEqual(parent.stat().st_uid, 0)
                self.assertEqual(parent.stat().st_mode & 0o022, 0)
        self.assertIsNone(self.controller.poll())
        self.assertEqual((ROOT / "root-secret").read_text(), "DUMMY_ROOT_CREDENTIAL\n")

    def test_01_exact_previous_root_execution_can_overwrite_root_helper(self):
        self.context("baseline")
        # Old setup checking was root too; this synthetic checker intentionally
        # requires UID10001, so omit it for the exact old run_squad red fixture.
        (self.repo / "scripts" / "check-hosted-squad-setup.mjs").unlink()
        helper = ROOT / "baseline-helper.py"
        helper.write_text("trusted before root model\n")
        helper.chmod(0o644)
        before = hashlib.sha256(helper.read_bytes()).hexdigest()
        result = subprocess.run(
            [
                "/bin/bash",
                "-c",
                (
                    "set -euo pipefail; source /ci/tests/.revision03-baseline-contract.sh; "
                    "die() { exit 1; }; log() { :; }; "
                    "COPILOT_TOKEN=fixture-copilot-secret; run_squad '@ripley fixture'"
                ),
            ],
            cwd=self.repo,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotEqual(hashlib.sha256(helper.read_bytes()).hexdigest(), before)
        self.assertEqual(helper.stat().st_uid, 0)
        self.unchanged()

    def test_02_model_permission_denials_and_trusted_publication(self):
        result = self.model()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        proof = json.loads((self.home / "proof.json").read_text())
        self.assertEqual(proof["uid"], 10001)
        self.assertTrue(proof["modelGitCommitSucceeded"])
        self.assertGreaterEqual(len(proof["denials"]), 16)
        self.assertTrue(all(proof["denials"].values()))
        self.unchanged()
        result = subprocess.run(
            [
                "/bin/bash",
                "-c",
                (
                    "set -euo pipefail; source /runtime-contract.sh; "
                    "PATH=/usr/local/bin:/usr/bin:/bin; "
                    f"TRUSTED_HOME={self.trusted_home}; PUBLICATION_HELPER=/readme-publication.py; "
                    "GITHUB_TOKEN=fixture-app-secret; COPILOT_TOKEN=fixture-copilot-secret; "
                    f"publication_python build {self.publisher} {self.repo} "
                    f"{self.base} {self.base} '{BOT}' '{EMAIL}'"
                ),
            ],
            cwd=self.repo / ".git",
            capture_output=True,
            text=True,
            check=True,
        )
        head = result.stdout.strip()
        self.assertEqual(git(self.publisher, "rev-parse", f"{head}^"), self.base)
        self.assertEqual(
            git(self.publisher, "log", "-1", "--format=%an|%cn|%B", head),
            f"{BOT}|{BOT}|squad: approved README update",
        )
        self.assertEqual(
            git(self.publisher, "diff", "--name-only", self.base, head), "README.md"
        )
        self.assertIn(
            "Genuine UID-isolated", git(self.publisher, "show", f"{head}:README.md")
        )
        for line in git(
            self.publisher,
            "cat-file",
            "--batch-all-objects",
            "--batch-check=%(objectname) %(objecttype)",
        ).splitlines():
            oid, kind = line.split()
            if kind in ("commit", "blob"):
                content = git(self.publisher, "cat-file", kind, oid)
                self.assertNotIn("DUMMY_MODEL_", content)
                self.assertNotIn("fixture-copilot-secret", content)
                self.assertNotIn("fixture-app-secret", content)
        print(
            "UID10001 positive Git/README + 16+ PermissionDenied attempts; protected hashes unchanged; trusted App-shaped history PASS"
        )

    def test_03_failed_native_execution_preserves_root_boundary(self):
        result = self.model("failure")
        self.assertEqual(result.returncode, 2)
        self.unchanged()
        self.assertEqual(git(self.publisher, "for-each-ref"), "")

    def test_04_model_parent_and_candidate_symlinks_fail_closed(self):
        shutil.rmtree(self.repo)
        self.repo.symlink_to(ROOT / "origin", target_is_directory=True)
        result = subprocess.run(
            [
                "/usr/bin/python3",
                "-I",
                "/model-execution.py",
                "prepare",
                str(self.repo),
                str(self.home),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((ROOT / "origin").stat().st_uid, 0)
        self.unchanged()

    def test_05_actual_worker_entrypoint_positive_and_empty_negative(self):
        spec = importlib.util.spec_from_file_location(
            "hosted_functional_fixtures", "/ci/tests/test_hosted_runtime.py"
        )
        fixtures = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fixtures)
        fixtures.ROOT = ROOT
        fixtures.RUNTIME_ROOT = Path("/")
        runner = ROOT / "agents" / "runner"
        runner.mkdir(parents=True)
        shutil.copyfile("/ci/agents/runner/entrypoint.sh", runner / "entrypoint.sh")
        for mode in ("readme", "empty"):
            with self.subTest(mode=mode):
                fixture = fixtures.HostedRuntimeTests()
                fixture.setUp()
                installed = []
                backup = ROOT / "tool-backups"
                backup.mkdir(mode=0o700)
                try:
                    fixture.target()
                    fixture.env["FIXTURE_MODE"] = mode
                    fixture.env["FIXTURE_MESSAGE"] = json.dumps(
                        [
                            {
                                "id": "message",
                                "popReceipt": "receipt",
                                "content": base64.b64encode(
                                    json.dumps(fixture.message).encode()
                                ).decode(),
                            }
                        ]
                    )
                    variables = {
                        key: value
                        for key, value in fixture.env.items()
                        if key.startswith("FIXTURE_")
                    }
                    variables.update(
                        ORIGINAL_GIT="/usr/bin/git", ORIGINAL_OPENSSL="/usr/bin/openssl"
                    )
                    (fixture.folder / "fixture-env.sh").write_text(
                        "".join(
                            f"export {key}={shlex.quote(value)}\n"
                            for key, value in variables.items()
                        )
                    )
                    # Replace only trusted tool paths in this disposable test
                    # container; the installed model launcher remains unmodified.
                    for name in (
                        "az",
                        "gh",
                        "curl",
                        "openssl",
                        "git",
                        "copilot",
                        "python3",
                    ):
                        tool = Path("/usr/local/bin") / name
                        if tool.exists() or tool.is_symlink():
                            tool.replace(backup / name)
                        installed.append(tool)
                        if name == "python3":
                            tool.write_text('#!/bin/sh\nexec /usr/bin/python3 "$@"\n')
                        else:
                            shutil.copyfile(fixture.bin / name, tool)
                            if name == "copilot":
                                tool.write_text(
                                    tool.read_text().replace(
                                        'case "$FIXTURE_MODE" in',
                                        '[[ "$(id -u)" == 10001 ]] || exit 103\ncase "$FIXTURE_MODE" in',
                                    )
                                )
                        tool.chmod(0o555)
                    result = subprocess.run(
                        ["/bin/bash", "/entrypoint.sh"],
                        env=fixture.env,
                        capture_output=True,
                        text=True,
                        cwd=fixture.folder,
                        timeout=45,
                        check=False,
                    )
                    if mode == "readme":
                        fixture.assert_trusted_published_history(result)
                    else:
                        fixture.assert_no_publication(result)
                        self.assertIn(
                            "Native Squad produced no changed files", result.stderr
                        )
                    self.unchanged()
                finally:
                    for tool in installed:
                        tool.unlink()
                        saved = backup / tool.name
                        if saved.exists() or saved.is_symlink():
                            saved.replace(tool)
                    backup.rmdir()
                    fixture.tearDown()
        print(
            "Actual /entrypoint.sh + unmodified UID launcher: native positive/empty negative PASS"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
