#!/usr/bin/env python3
"""Safe multi-repo git sync for Obsidian vaults.

Usage:
  vault_sync.py status [--repo NAME] [--no-fetch]
  vault_sync.py diff   [--repo NAME]
  vault_sync.py pull   [--repo NAME]
  vault_sync.py commit --repo NAME [-m MESSAGE]
  vault_sync.py push   --repo NAME

Safety: never force-pushes, never resets, never resolves conflicts.
A failed rebase is aborted so the repo is left exactly as it was.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from vaultlib import load_repo_config, select_repos  # noqa: E402


def git(path: Path, *args: str, timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(path), *args],
        capture_output=True, text=True, timeout=timeout,
    )


def is_repo(r: dict) -> str | None:
    if not r["path"].is_dir():
        return f"path not found: {r['path']}"
    if git(r["path"], "rev-parse", "--is-inside-work-tree").returncode != 0:
        return "not a git repository"
    return None


def dirty_files(path: Path) -> list[str]:
    return [l for l in git(path, "status", "--porcelain").stdout.splitlines() if l.strip()]


def current_branch(path: Path) -> str:
    return git(path, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()


def ahead_behind(r: dict) -> tuple[str, str]:
    up = f"{r['remote']}/{r['branch']}"
    p = git(r["path"], "rev-list", "--left-right", "--count", f"HEAD...{up}")
    if p.returncode != 0:
        return "?", "?"
    a, b = p.stdout.split()
    return a, b


def cmd_status(repos, fetch: bool):
    rows = [("repo", "branch", "ahead", "behind", "state")]
    for r in repos:
        err = is_repo(r)
        if err:
            rows.append((r["name"], "-", "-", "-", f"ERROR: {err}"))
            continue
        if fetch:
            f = git(r["path"], "fetch", r["remote"], "--quiet", timeout=45)
            if f.returncode != 0:
                note = " (fetch failed)"
            else:
                note = ""
        else:
            note = ""
        a, b = ahead_behind(r)
        d = dirty_files(r["path"])
        state = (f"dirty ({len(d)} files)" if d else "clean") + note
        rows.append((r["name"], current_branch(r["path"]), a, b, state))
    widths = [max(len(str(row[i])) for row in rows) for i in range(5)]
    for row in rows:
        print("  ".join(str(c).ljust(widths[i]) for i, c in enumerate(row)))


def cmd_diff(repos):
    for r in repos:
        err = is_repo(r)
        print(f"== {r['name']} ==")
        if err:
            print(f"  ERROR: {err}")
            continue
        d = dirty_files(r["path"])
        print("  (clean)" if not d else "\n".join(f"  {l}" for l in d))


def cmd_pull(repos):
    for r in repos:
        err = is_repo(r)
        if err:
            print(f"[{r['name']}] ERROR: {err}")
            continue
        if dirty_files(r["path"]):
            print(f"[{r['name']}] SKIPPED: uncommitted changes (commit or stash first)")
            continue
        p = git(r["path"], "pull", "--rebase", r["remote"], r["branch"], timeout=120)
        if p.returncode == 0:
            print(f"[{r['name']}] OK: {p.stdout.strip().splitlines()[-1] if p.stdout.strip() else 'up to date'}")
        else:
            git(r["path"], "rebase", "--abort")
            print(f"[{r['name']}] CONFLICT/ERROR: rebase aborted, repo unchanged.\n  {p.stderr.strip()[:400]}")


def cmd_commit(repos, message: str | None):
    r = repos[0]
    err = is_repo(r)
    if err:
        sys.exit(f"[{r['name']}] ERROR: {err}")
    d = dirty_files(r["path"])
    if not d:
        print(f"[{r['name']}] nothing to commit")
        return
    prefix = load_repo_config(r["path"])["sync"]["commit_prefix"]
    msg = message or f"{len(d)} file(s) changed ({date.today().isoformat()})"
    if not msg.startswith(f"{prefix}:"):
        msg = f"{prefix}: {msg}"
    git(r["path"], "add", "-A")
    p = git(r["path"], "commit", "-m", msg)
    print(f"[{r['name']}] {'committed: ' + msg if p.returncode == 0 else 'FAILED: ' + p.stderr.strip()}")


def cmd_push(repos):
    r = repos[0]
    err = is_repo(r)
    if err:
        sys.exit(f"[{r['name']}] ERROR: {err}")
    p = git(r["path"], "push", r["remote"], r["branch"], timeout=120)  # never --force
    print(f"[{r['name']}] {'pushed' if p.returncode == 0 else 'FAILED: ' + p.stderr.strip()[:400]}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["status", "diff", "pull", "commit", "push"])
    ap.add_argument("--repo", help="repo name from repos.toml (default: all, except commit/push)")
    ap.add_argument("-m", "--message")
    ap.add_argument("--no-fetch", action="store_true")
    a = ap.parse_args()

    if a.command in ("commit", "push") and not a.repo:
        sys.exit(f"'{a.command}' requires --repo NAME (one repo at a time, on purpose).")
    repos = select_repos(a.repo)
    {
        "status": lambda: cmd_status(repos, not a.no_fetch),
        "diff": lambda: cmd_diff(repos),
        "pull": lambda: cmd_pull(repos),
        "commit": lambda: cmd_commit(repos, a.message),
        "push": lambda: cmd_push(repos),
    }[a.command]()


if __name__ == "__main__":
    main()
