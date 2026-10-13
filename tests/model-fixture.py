"""Portable functional fixture, NOT a Linux UID/isolation test.

The separate actual-image suite exercises unmodified setpriv and filesystem DAC.
This adapter runs the same environment/argument construction without host user
creation, ownership changes or privilege operations.
"""

import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

helper, operation, repo, home, *arguments = sys.argv[2:]
spec = importlib.util.spec_from_file_location("model_execution", helper)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
folder = Path(repo).parent.parent
module.protected_parent = lambda path: None
module.MODEL_UID = Path(repo).stat().st_uid
module.MODEL_GID = Path(repo).stat().st_gid
module.os.chown = lambda *args, **kwargs: None


def execute(command, cwd, environment, timeout):
    assert set(environment) <= {
        "PATH",
        "HOME",
        "USER",
        "LOGNAME",
        "TMPDIR",
        "XDG_CONFIG_HOME",
        "LC_ALL",
        "GIT_CONFIG_NOSYSTEM",
        "GIT_CONFIG_GLOBAL",
        "GIT_TERMINAL_PROMPT",
        "COPILOT_GITHUB_TOKEN",
    }
    bash = (
        r"C:\Program Files\Git\bin\bash.exe"
        if os.name == "nt"
        else shutil.which("bash")
    )
    environment = dict(environment)
    environment["PATH"] = str(folder / "bin") + os.pathsep + os.environ["PATH"]
    if os.name == "nt":
        environment["SystemRoot"] = os.environ["SystemRoot"]
    if command[1] == "/model-profile.sh":
        contract = Path(helper).with_name("runtime-contract.sh").as_posix()
        command = [
            bash,
            "-c",
            (f'source "{contract}"; ' "die() { exit 1; }; require_native_squad"),
        ]
    else:
        command = [bash, str(folder / "bin" / "copilot"), *command[1:]]
    try:
        return subprocess.run(
            command,
            cwd=cwd,
            env=environment,
            capture_output=True,
            timeout=timeout,
            check=False,
        ).returncode
    except subprocess.TimeoutExpired:
        return 124


module.execute = execute
if operation == "prepare":
    module.prepare(Path(repo), Path(home))
    sys.exit(0)
sys.exit(module.run(Path(repo), Path(home), int(arguments[0])))
