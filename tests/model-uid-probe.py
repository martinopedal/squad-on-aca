"""Credential-free adversarial child, executed only in the disposable CI image."""

import json
import os
import signal
import stat
import subprocess
from pathlib import Path

ROOT = Path("/workspace/uid-tests")
context = json.loads((ROOT / "probe-context.json").read_text())
if context["mode"] == "baseline":
    assert os.getuid() == 0
    (ROOT / "baseline-helper.py").write_text("DUMMY_ROOT_OVERWRITE\n")
    raise SystemExit(0)

assert os.getuid() == os.geteuid() == 10001
assert os.getgid() == os.getegid() == 10001
assert set(os.getgroups()) <= {10001}
status = Path("/proc/self/status").read_text()
for field in ("CapInh", "CapPrm", "CapEff", "CapBnd", "CapAmb"):
    assert int(status.split(field + ":")[1].splitlines()[0].strip(), 16) == 0
assert status.split("NoNewPrivs:")[1].splitlines()[0].strip() == "1"
assert os.environ["COPILOT_GITHUB_TOKEN"] == "fixture-copilot-secret"
for key in (
    "GH_TOKEN",
    "GITHUB_TOKEN",
    "COPILOT_TOKEN",
    "IDENTITY_HEADER",
    "MSI_SECRET",
    "IDENTITY_ENDPOINT",
    "AZURE_CLIENT_ID",
    "PYTHONPATH",
    "BASH_ENV",
    "LD_PRELOAD",
    "DUMMY_ROOT_MARKER",
):
    assert key not in os.environ
assert "--agent" in os.sys.argv and "Squad" in os.sys.argv
assert (
    "--secret-env-vars=COPILOT_GITHUB_TOKEN,IDENTITY_HEADER,MSI_SECRET" in os.sys.argv
)

denials = {}


def denied(name, operation):
    try:
        operation()
    except PermissionError:
        denials[name] = True
    else:
        raise AssertionError("Protected operation unexpectedly succeeded: " + name)


for name in (
    "/readme-publication.py",
    "/entrypoint.sh",
    "/runtime-contract.sh",
    "/github-app.sh",
    "/model-execution.py",
    "/model-profile.sh",
):
    denied("overwrite:" + name, lambda name=name: os.open(name, os.O_WRONLY))
denied(
    "replace-helper",
    lambda: os.replace(Path.cwd() / "README.md", "/readme-publication.py"),
)
denied(
    "install-write", lambda: (Path("/usr/local/bin") / "model-hook").write_text("bad")
)
denied(
    "install-parent-rename", lambda: os.rename("/usr/local/bin", "/usr/local/model-bin")
)
denied(
    "workspace-parent-write", lambda: (ROOT / "model-parent-write").write_text("bad")
)
denied("publisher-write", lambda: (ROOT / "publisher" / "hook").write_text("bad"))
denied(
    "publisher-rename", lambda: os.rename(ROOT / "publisher", ROOT / "model-publisher")
)
denied("root-credential", lambda: (ROOT / "root-secret").read_bytes())
denied("root-home", lambda: Path("/root").iterdir().__next__())
denied(
    "root-environment",
    lambda: Path(f"/proc/{context['controller']}/environ").read_bytes(),
)
denied("kill-controller", lambda: os.kill(context["controller"], signal.SIGTERM))
denied("setuid-root", lambda: os.setuid(0))
assert not Path("/usr/bin/sudo").exists()
assert not Path("/usr/bin/su").stat().st_mode & (stat.S_ISUID | stat.S_ISGID)
assert (
    subprocess.run(
        ["/usr/bin/su", "-c", "id -u"],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        timeout=5,
        check=False,
    ).returncode
    != 0
)

readme = Path("README.md")
readme.write_text(readme.read_text() + "Genuine UID-isolated README work.\n")
subprocess.run(["git", "add", "README.md"], check=True, capture_output=True)
subprocess.run(
    ["git", "commit", "-qm", "DUMMY_MODEL_COMMIT"], check=True, capture_output=True
)
# Root publication must neither read model Git metadata nor import modules here.
Path(".git/json.py").write_text("raise RuntimeError('MODEL_MODULE_IMPORTED')\n")
Path(".git/model-hooks").mkdir()
hook = Path(".git/model-hooks/pre-push")
hook.write_text("#!/bin/sh\nexit 89\n")
hook.chmod(0o755)
subprocess.run(
    ["git", "config", "core.hooksPath", str(hook.parent.resolve())], check=True
)
subprocess.run(
    ["git", "config", "remote.origin.url", "https://example.invalid/model"], check=True
)
subprocess.run(["git", "config", "user.name", "DUMMY_MODEL_AUTHOR"], check=True)
(Path(os.environ["HOME"]) / "proof.json").write_text(
    json.dumps(
        {
            "uid": os.getuid(),
            "gid": os.getgid(),
            "capabilities": "zero",
            "noNewPrivileges": True,
            "modelGitCommitSucceeded": True,
            "denials": denials,
        }
    )
)
if context["mode"] == "failure":
    raise SystemExit(2)
