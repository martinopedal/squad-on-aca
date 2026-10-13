"""Launch native Squad with a fixed Linux identity and an allowlisted environment."""

import os
import signal
import stat
import subprocess
import sys
from pathlib import Path

MODEL_UID = 10001
MODEL_GID = 10001
MODEL_PATH = "/usr/local/go/bin:/usr/local/bin:/usr/bin:/bin"
DROP_PRIVILEGES = [
    "/usr/bin/setpriv",
    f"--reuid={MODEL_UID}",
    f"--regid={MODEL_GID}",
    "--clear-groups",
    "--no-new-privs",
    "--inh-caps=-all",
    "--ambient-caps=-all",
    "--bounding-set=-all",
]


def protected_parent(path: Path) -> None:
    for parent in (path.parent, *path.parent.parents):
        info = parent.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & 0o022:
            raise ValueError("Model paths require root-protected parent directories.")


def prepare(repo: Path, home: Path) -> None:
    protected_parent(repo)
    protected_parent(home)
    if not stat.S_ISDIR(repo.lstat().st_mode):
        raise ValueError("Candidate must be a fresh directory, not a symlink.")
    home.mkdir(mode=0o700)
    (home / "tmp").mkdir(mode=0o700)
    # Only the newly cloned candidate and fresh home change ownership. Never
    # follow target symlinks or chown the workspace/publisher/install tree.
    for folder in (repo, home):
        for directory, dirs, files in os.walk(folder, followlinks=False):
            for name in dirs + files:
                os.chown(
                    Path(directory) / name, MODEL_UID, MODEL_GID, follow_symlinks=False
                )
            os.chown(directory, MODEL_UID, MODEL_GID, follow_symlinks=False)
    repo.chmod(0o700)


def execute(command: list[str], repo: Path, environment: dict, timeout: int) -> int:
    process = subprocess.Popen(
        DROP_PRIVILEGES + command,
        cwd=repo,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
        umask=0o077,
    )
    try:
        return process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        return 124
    finally:
        # Clean up ordinary CLI/tool children even when the CLI exits first.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()


def run(repo: Path, home: Path, timeout: int) -> int:
    protected_parent(repo)
    protected_parent(home)
    for path in (repo, home):
        info = path.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != MODEL_UID:
            raise ValueError("Model directory ownership is not qualified.")
    token = sys.stdin.readline().rstrip("\n")
    prompt = sys.stdin.read()
    if not token or not prompt or not 1 <= timeout <= 480:
        raise ValueError("Invalid native execution input.")
    environment = {
        "PATH": MODEL_PATH,
        "HOME": str(home),
        "USER": "squad-model",
        "LOGNAME": "squad-model",
        "TMPDIR": str(home / "tmp"),
        "XDG_CONFIG_HOME": str(home / ".config"),
        "LC_ALL": "C",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": str(home / ".gitconfig"),
        "GIT_TERMINAL_PROMPT": "0",
    }
    # Repository setup/checker code is also unprivileged, without any credential.
    checked = execute(
        ["/bin/bash", "/model-profile.sh"], repo, environment, min(timeout, 30)
    )
    if checked:
        return checked
    environment["COPILOT_GITHUB_TOKEN"] = token
    return execute(
        [
            "/usr/local/bin/copilot",
            "--yolo",
            "--agent",
            "Squad",
            "--no-auto-update",
            "--no-remote-export",
            "--log-level",
            "none",
            "--secret-env-vars=COPILOT_GITHUB_TOKEN,IDENTITY_HEADER,MSI_SECRET",
            "--deny-tool=shell(az:*)",
            "--deny-tool=shell(gh:*)",
            "--deny-tool=shell(curl:*)",
            "--deny-tool=shell(wget:*)",
            "--deny-tool=shell(git push:*)",
            "-p",
            prompt,
        ],
        repo,
        environment,
        timeout,
    )


def main() -> int:
    if os.name != "posix" or os.geteuid() != 0:
        raise ValueError("Native execution requires the Linux root controller.")
    operation, repo, home, *arguments = sys.argv[1:]
    if operation == "prepare" and not arguments:
        prepare(Path(repo), Path(home))
        return 0
    if operation == "run" and len(arguments) == 1:
        return run(Path(repo), Path(home), int(arguments[0]))
    raise ValueError("Unknown native execution operation.")


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, subprocess.SubprocessError):
        print("Unprivileged native execution failed.", file=sys.stderr)
        sys.exit(1)
