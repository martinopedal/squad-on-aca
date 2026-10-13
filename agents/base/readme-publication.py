"""Import README bytes, never model Git objects, into a qualified target tree."""

import hashlib
import os
import re
import stat
import subprocess
import sys
from pathlib import Path

MESSAGE = b"squad: approved README update\n"
MAX_README = 1024 * 1024


def git(repo: str, *args: str, data: bytes | None = None) -> bytes:
    return subprocess.run(
        [
            "git",
            "-c",
            "core.hooksPath=/dev/null",
            "-c",
            "core.autocrlf=false",
            "-c",
            "commit.gpgsign=false",
            "-c",
            "core.attributesFile=/dev/null",
            "-C",
            str(repo),
            *args,
        ],
        input=data,
        capture_output=True,
        check=True,
    ).stdout


def validate_readme(data: bytes) -> None:
    if len(data) > MAX_README or b"\0" in data:
        raise ValueError("README must remain text within the size bound.")
    try:
        data.decode("utf-8")
    except UnicodeError:
        raise ValueError("README must remain text (UTF-8).") from None
    for name in ("GITHUB_TOKEN", "COPILOT_TOKEN"):
        secret = os.environ.get(name, "").encode()
        if secret and secret in data:
            raise ValueError("Credential content detected in README.")
    if re.search(
        rb"-----BEGIN .*PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}",
        data,
    ):
        raise ValueError("Credential pattern detected in README.")


def tree(repo: str, ref: str) -> dict[str, tuple[bytes, bytes]]:
    entries = {}
    for entry in git(repo, "ls-tree", "-rz", "--full-tree", ref).split(b"\0"):
        if entry:
            metadata, path = entry.split(b"\t", 1)
            mode, kind, oid = metadata.split()
            if kind != b"blob":
                raise ValueError("Unsupported target tree entry.")
            entries[os.fsdecode(path)] = (mode, oid)
    return entries


def blobs(repo: str, entries: dict[str, tuple[bytes, bytes]]) -> dict[str, bytes]:
    ids = [oid for _, oid in entries.values()]
    result = git(repo, "cat-file", "--batch", data=b"\n".join(ids) + b"\n")
    values = {}
    offset = 0
    for path in entries:
        end = result.index(b"\n", offset)
        size = int(result[offset:end].split()[2])
        offset = end + 1
        values[path] = result[offset : offset + size]
        offset += size + 1
    return values


def qualify_previous(repo: str, base: str, parent: str, bot: str, email: str) -> None:
    git(repo, "merge-base", "--is-ancestor", base, parent)
    previous = base
    identity = re.escape(f"{bot} <{email}>".encode())
    for oid in git(repo, "rev-list", "--reverse", f"{base}..{parent}").splitlines():
        raw = git(repo, "cat-file", "commit", oid.decode())
        pattern = (
            rb"tree [0-9a-f]{40}\nparent "
            + previous.encode()
            + rb"\nauthor "
            + identity
            + rb" [0-9]+ \+0000\ncommitter "
            + identity
            + rb" [0-9]+ \+0000\n\n"
            + re.escape(MESSAGE)
        )
        if not re.fullmatch(pattern, raw):
            raise ValueError("Previous PR is not trusted wrapper-only history.")
        if (
            git(
                repo,
                "diff-tree",
                "--no-commit-id",
                "--name-only",
                "-r",
                previous,
                oid.decode(),
            ).strip()
            != b"README.md"
        ):
            raise ValueError("Previous PR violated README-only scope.")
        entry = tree(repo, oid.decode()).get("README.md")
        if not entry or entry[0] != b"100644":
            raise ValueError("Previous README must remain a regular file.")
        validate_readme(git(repo, "cat-file", "blob", entry[1].decode()))
        previous = oid.decode()
    if previous != parent:
        raise ValueError("Previous PR has an unqualified parent.")


def candidate_files(folder: Path) -> dict[str, Path]:
    found = {}
    for directory, dirs, files in os.walk(folder, followlinks=False):
        if Path(directory) == folder:
            dirs[:] = [name for name in dirs if name != ".git"]
            files = [name for name in files if name != ".git"]
        for name in list(dirs):
            path = Path(directory) / name
            if path.is_symlink():
                files.append(name)
                dirs.remove(name)
        for name in files:
            path = Path(directory) / name
            found[path.relative_to(folder).as_posix()] = path
    return found


def read_regular(path: Path, limit: int, candidate: Path) -> bytes:
    if not stat.S_ISREG(path.lstat().st_mode):
        raise ValueError("README must remain a regular file.")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    if os.name == "posix":
        # A surviving model process may race directory components. Resolve every
        # component by descriptor without following links into root-only paths.
        directory = os.open(candidate, flags | os.O_DIRECTORY)
        try:
            parts = path.relative_to(candidate).parts
            for part in parts[:-1]:
                child = os.open(part, flags | os.O_DIRECTORY, dir_fd=directory)
                os.close(directory)
                directory = child
            fd = os.open(parts[-1], flags, dir_fd=directory)
        finally:
            os.close(directory)
    else:
        fd = os.open(path, flags | getattr(os, "O_BINARY", 0))
    with os.fdopen(fd, "rb") as handle:
        if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
            raise ValueError("README must remain a regular file.")
        return handle.read(limit + 1)


def import_readme(repo: str, candidate: Path, parent: str) -> str:
    entries = tree(repo, parent)
    contents = blobs(repo, entries)
    files = candidate_files(candidate)
    if set(files) != set(entries):
        raise ValueError("README-only scope violated.")
    for path, (mode, _) in entries.items():
        if path == "README.md":
            continue
        file = files[path]
        if mode == b"120000":
            data = os.fsencode(os.readlink(file)) if file.is_symlink() else b""
        else:
            data = read_regular(file, len(contents[path]), candidate)
            if os.name != "nt" and bool(file.stat().st_mode & 0o111) != (
                mode == b"100755"
            ):
                raise ValueError("README-only scope violated.")
        if hashlib.sha256(data).digest() != hashlib.sha256(contents[path]).digest():
            raise ValueError("README-only scope violated.")
    if entries.get("README.md", (None,))[0] != b"100644":
        raise ValueError("Qualified README must be a regular file.")
    data = read_regular(files["README.md"], MAX_README, candidate)
    validate_readme(data)
    if data == contents["README.md"]:
        raise ValueError("Native Squad produced no changed files; no fallback PR.")
    git(repo, "read-tree", parent)
    oid = (
        git(repo, "hash-object", "--no-filters", "-w", "--stdin", data=data)
        .strip()
        .decode()
    )
    git(repo, "update-index", "--add", "--cacheinfo", f"100644,{oid},README.md")
    return git(repo, "write-tree").strip().decode()


def main() -> None:
    operation, repo, candidate, base, parent, bot, email = sys.argv[1:]
    qualify_previous(repo, base, parent, bot, email)
    if operation == "qualify":
        return
    new_tree = import_readme(repo, Path(candidate), parent)
    os.environ.update(
        GIT_AUTHOR_NAME=bot,
        GIT_COMMITTER_NAME=bot,
        GIT_AUTHOR_EMAIL=email,
        GIT_COMMITTER_EMAIL=email,
    )
    # UTC prevents local/model configuration from controlling commit metadata.
    timestamp = (
        git(repo, "var", "GIT_AUTHOR_IDENT").decode().rsplit("> ", 1)[1].split()[0]
    )
    os.environ.update(
        GIT_AUTHOR_DATE=f"{timestamp} +0000", GIT_COMMITTER_DATE=f"{timestamp} +0000"
    )
    print(
        git(repo, "commit-tree", new_tree, "-p", parent, data=MESSAGE).strip().decode()
    )


if __name__ == "__main__":
    try:
        main()
    except ValueError as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
    except (OSError, subprocess.SubprocessError, KeyError):
        print(
            "Controlled publication failed; no model details exported.", file=sys.stderr
        )
        sys.exit(1)
