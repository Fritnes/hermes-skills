#!/usr/bin/env python3
"""Fetch registered Git repos and report whether their branches need updating."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_CONFIG = Path.home() / ".hermes" / "git-repos.toml"


@dataclass(frozen=True)
class Repository:
    name: str
    description: str
    remote: str
    local_path: str
    branch: str | None


def run_git(path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(path), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def git_output(path: Path, *args: str) -> str:
    result = run_git(path, *args)
    if result.returncode != 0:
        raise RuntimeError(f"Git command failed: {args[0]}.")
    return result.stdout.strip()


def load_repositories(config_path: Path) -> list[Repository]:
    try:
        with config_path.open("rb") as config_file:
            config: dict[str, Any] = tomllib.load(config_file)
    except OSError as error:
        raise ValueError(f"Cannot read registry: {config_path}") from error
    except tomllib.TOMLDecodeError as error:
        raise ValueError(f"Invalid TOML in registry: {config_path}") from error

    entries = config.get("repositories")
    if not isinstance(entries, dict) or not entries:
        raise ValueError("Registry has no [repositories.*] entries.")

    repositories: list[Repository] = []
    for key, entry in entries.items():
        if not isinstance(entry, dict):
            raise ValueError(f"Repository entry {key!r} must be a TOML table.")

        required = ("name", "description", "remote", "local_path")
        values = {field: entry.get(field) for field in required}
        if any(not isinstance(value, str) or not value.strip() for value in values.values()):
            raise ValueError(f"Repository {key!r} needs name, description, remote, and local_path strings.")
        if values["name"] != key:
            raise ValueError(f"Repository table key and name must match for {key!r}.")

        branch = entry.get("branch")
        if branch is not None and (not isinstance(branch, str) or not branch.strip()):
            raise ValueError(f"Repository {key!r} has an invalid branch value.")

        repositories.append(
            Repository(
                name=values["name"],
                description=values["description"],
                remote=values["remote"],
                local_path=values["local_path"],
                branch=branch,
            )
        )
    return repositories


def matching_remote(path: Path, expected_url: str) -> str | None:
    for remote_name in git_output(path, "remote").splitlines():
        urls = git_output(path, "remote", "get-url", "--all", remote_name).splitlines()
        if expected_url in urls:
            return remote_name
    return None


def check_repository(repository: Repository, synchronize: bool = False) -> bool:
    path = Path(repository.local_path).expanduser()
    if not path.is_absolute():
        print(f"{repository.name}: ERROR: local_path must be absolute.")
        return False
    if not path.is_dir():
        print(f"{repository.name}: ERROR: configured local path does not exist.")
        return False

    try:
        root = Path(git_output(path, "rev-parse", "--show-toplevel")).resolve()
        if root != path.resolve():
            print(f"{repository.name}: ERROR: local_path is not the Git repository root.")
            return False

        remote_name = matching_remote(path, repository.remote)
        if remote_name is None:
            print(f"{repository.name}: ERROR: configured remote does not match a Git remote.")
            return False

        current_branch = run_git(path, "symbolic-ref", "--quiet", "--short", "HEAD")
        branch = repository.branch or current_branch.stdout.strip()
        if not branch:
            print(f"{repository.name}: ERROR: detached HEAD; configure a branch to check.")
            return False
        if run_git(path, "check-ref-format", "--branch", branch).returncode != 0:
            print(f"{repository.name}: ERROR: invalid branch name in registry.")
            return False

        local_ref = f"refs/heads/{branch}"
        if run_git(path, "show-ref", "--verify", "--quiet", local_ref).returncode != 0:
            print(f"{repository.name}: ERROR: local branch {branch!r} does not exist.")
            return False

        worktree = "dirty" if git_output(path, "status", "--porcelain") else "clean"
        fetch = run_git(path, "fetch", "--quiet", "--no-tags", remote_name, f"refs/heads/{branch}")
        if fetch.returncode != 0:
            print(f"{repository.name}: ERROR: fetch failed; check remote availability and Git authentication.")
            return False

        remote_commit = git_output(path, "rev-parse", "--verify", "FETCH_HEAD^{commit}")
        counts = git_output(path, "rev-list", "--left-right", "--count", f"{local_ref}...{remote_commit}")
        ahead, behind = (int(count) for count in counts.split())

        if ahead and behind:
            state = f"DIVERGED (local +{ahead}, remote +{behind})"
        elif behind:
            state = f"UPDATE AVAILABLE ({behind} commit(s) behind)"
        elif ahead:
            state = f"AHEAD ({ahead} commit(s) to push)"
        else:
            state = "UP TO DATE"

        current_name = current_branch.stdout.strip() or "detached HEAD"
        if synchronize:
            if worktree != "clean":
                state += "; not synced because worktree is dirty"
            elif current_name != branch:
                state += "; not synced because another branch is checked out"
            elif ahead and behind:
                state += "; manual reconciliation required"
            elif behind:
                pull = run_git(path, "merge", "--ff-only", remote_commit)
                if pull.returncode == 0:
                    state = f"PULLED {behind} commit(s)"
                else:
                    state += "; fast-forward failed, no changes applied"
            elif ahead:
                push = run_git(path, "push", remote_name, f"{local_ref}:refs/heads/{branch}")
                if push.returncode == 0:
                    state = f"PUSHED {ahead} commit(s)"
                else:
                    state += "; push rejected or failed, check remote status"

        checked_branch = branch
        if current_name != branch:
            checked_branch += f", currently on {current_name}"
        print(f"{repository.name}: {state} [{checked_branch}; worktree {worktree}]")
        return True
    except (OSError, RuntimeError) as error:
        print(f"{repository.name}: ERROR: {error}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check registered repositories or synchronize safe fast-forward changes."
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="registry TOML path")
    parser.add_argument("--repo", help="check or sync only this repository name")
    parser.add_argument(
        "--sync",
        action="store_true",
        help="fast-forward pull or push when safe; stop on dirty or diverged repos",
    )
    args = parser.parse_args()

    try:
        repositories = load_repositories(args.config.expanduser())
    except ValueError as error:
        parser.error(str(error))

    if args.repo:
        repositories = [repository for repository in repositories if repository.name == args.repo]
        if not repositories:
            parser.error(f"repository {args.repo!r} is not registered")

    success = True
    for repository in repositories:
        success = check_repository(repository, synchronize=args.sync) and success
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
