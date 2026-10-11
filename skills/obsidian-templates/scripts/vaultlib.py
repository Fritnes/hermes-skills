#!/usr/bin/env python3
"""Shared helpers for the Obsidian vault skills (stdlib only, Python 3.11+).

Config locations
    Git repo registry: ~/.hermes/git-repos.toml       (which repos exist, where)
  Per-repo config : <repo>/.vault.toml              (conventions for that repo)
  Index cache     : ~/.hermes/vault/index.json      (generated, safe to delete)

Override repo registry with HERMES_GIT_REPOS_FILE and vault cache/settings with HERMES_VAULT_DIR.
"""
from __future__ import annotations

import copy
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    sys.exit("Python 3.11+ is required (needs the stdlib 'tomllib' module).")

CONFIG_DIR = Path(os.environ.get("HERMES_VAULT_DIR", "~/.hermes/vault")).expanduser()
REGISTRY = Path(os.environ.get("HERMES_GIT_REPOS_FILE", "~/.hermes/git-repos.toml")).expanduser()
INDEX_FILE = CONFIG_DIR / "index.json"
CONVENTIONS_FILE = CONFIG_DIR / "conventions.md"
REPO_CONFIG_NAME = ".vault.toml"

DEFAULTS: dict = {
    "repo": {
        "type": "notes",
        "ignore": [".obsidian", ".git", ".trash", "attachments", "node_modules"],
        "templates_dir": "templates",
    },
    "folders": {
        "daily": "daily",
        "meeting": "meetings",
        "project": "projects",
        "idea": "ideas",
        "inbox": "inbox",
    },
    "naming": {
        "daily": "{date}",
        "meeting": "{date} {title}",
        "project": "{title}",
        "idea": "{title}",
        "inbox": "{title}",
    },
    "lint": {
        "required_keys": ["tags"],
        "orphan_ignore_folders": ["daily", "templates", "inbox"],
    },
    "sync": {"commit_prefix": "notes", "auto_push": False},
}


# --------------------------------------------------------------------------- config
def _merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def _git_output(path: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(path), *args], capture_output=True, text=True, check=False
        )
    except OSError:
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def _all_repos() -> list[dict]:
    if not REGISTRY.exists():
        sys.exit(
            f"NOT CONFIGURED: no registry at {REGISTRY}.\n"
            "Register local repositories with the git-repo-sync skill first."
        )
    try:
        data = tomllib.loads(REGISTRY.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        sys.exit(f"Cannot read Git repository registry {REGISTRY}: {error}")

    entries = data.get("repositories")
    if not isinstance(entries, dict):
        sys.exit(f"Invalid Git repository registry {REGISTRY}: expected [repositories.<name>] tables.")

    repos = []
    for key, entry in entries.items():
        if not isinstance(entry, dict):
            sys.exit(f"Invalid repository entry {key!r} in {REGISTRY}.")
        name = entry.get("name")
        description = entry.get("description")
        remote_url = entry.get("remote")
        local_path = entry.get("local_path")
        if key != name or not all(isinstance(value, str) and value.strip() for value in (name, description, remote_url, local_path)):
            sys.exit(f"Repository {key!r} needs matching name and table key, description, remote, and local_path.")
        if not Path(local_path).expanduser().is_absolute():
            sys.exit(f"Repository {name!r} must use an absolute local_path.")

        path = Path(local_path).expanduser()
        branch = entry.get("branch")
        if branch is not None and (not isinstance(branch, str) or not branch.strip()):
            sys.exit(f"Repository {name!r} has an invalid branch.")
        if not branch:
            current = _git_output(path, "rev-parse", "--abbrev-ref", "HEAD")
            branch = current if current and current != "HEAD" else "main"

        remote_name = None
        for candidate in _git_output(path, "remote").splitlines():
            urls = _git_output(path, "remote", "get-url", "--all", candidate).splitlines()
            if remote_url in urls:
                remote_name = candidate
                break

        obsidian_flag = entry.get("obsidian", False)
        if not isinstance(obsidian_flag, bool):
            sys.exit(f"Repository {name!r} has an invalid obsidian flag; use true or false.")
        is_obsidian = obsidian_flag or (path / ".obsidian").is_dir() or (path / REPO_CONFIG_NAME).is_file()
        repos.append(
            {
                "name": name,
                "description": description,
                "path": path,
                "branch": branch,
                "remote": remote_name or "origin",
                "remote_url": remote_url,
                "remote_matches": remote_name is not None,
                "obsidian": is_obsidian,
            }
        )
    return repos


def load_registry() -> list[dict]:
    repos = [repo for repo in _all_repos() if repo["obsidian"]]
    if not repos:
        sys.exit(
            f"No Obsidian vaults found in {REGISTRY}. Add `obsidian = true` to a repository entry, "
            "or ensure its local repo contains `.obsidian/` or `.vault.toml`."
        )
    return repos


def select_repos(name: str | None) -> list[dict]:
    repos = _all_repos() if name else load_registry()
    if not name:
        return repos
    found = [r for r in repos if r["name"] == name]
    if not found:
        sys.exit(f"Unknown repo '{name}'. Known: {', '.join(r['name'] for r in repos)}")
    return found


def load_repo_config(repo_path: Path) -> dict:
    cfg = copy.deepcopy(DEFAULTS)
    f = repo_path / REPO_CONFIG_NAME
    if f.exists():
        cfg = _merge(cfg, tomllib.loads(f.read_text(encoding="utf-8")))
    return cfg


# --------------------------------------------------------------------------- parsing
FM_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", re.S)
FENCE_RE = re.compile(r"```.*?```|~~~.*?~~~", re.S)
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
WIKILINK_RE = re.compile(r"!?\[\[([^\]|#^]+)(?:[#^][^\]|]*)?(?:\|[^\]]*)?\]\]")
TAG_RE = re.compile(r"(?<![\w/&#])#([A-Za-z][\w/-]*)")
HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$", re.M)
NON_NOTE_EXT = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".pdf", ".mp3", ".mp4",
    ".wav", ".mov", ".webm", ".excalidraw", ".canvas", ".csv", ".zip",
}


def _scalar(v: str):
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    if v.lower() in ("true", "false"):
        return v.lower() == "true"
    return v


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Minimal YAML-frontmatter parser: scalars, [a, b] lists, and '- item' lists."""
    m = FM_RE.match(text)
    if not m:
        return {}, text
    fm: dict = {}
    key = None
    for line in m.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        item = re.match(r"^\s+-\s+(.*)$", line)
        if item and key is not None:
            if not isinstance(fm.get(key), list):
                fm[key] = []
            fm[key].append(_scalar(item.group(1)))
            continue
        kv = re.match(r"^([\w\-. ]+?):\s*(.*)$", line)
        if kv:
            key, val = kv.group(1).strip(), kv.group(2).strip()
            if val.startswith("[") and val.endswith("]"):
                fm[key] = [_scalar(x) for x in val[1:-1].split(",") if x.strip()]
            elif val == "":
                fm[key] = ""
            else:
                fm[key] = _scalar(val)
    return fm, text[m.end():]


def parse_note(path: Path, root: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    fm, body = parse_frontmatter(text)
    clean = INLINE_CODE_RE.sub("", FENCE_RE.sub("", body))

    tags = fm.get("tags", [])
    if isinstance(tags, str):
        tags = [t.strip().lstrip("#") for t in re.split(r"[,\s]+", tags) if t.strip()]
    tags = [str(t).lstrip("#") for t in tags]
    tags += TAG_RE.findall(clean)

    links = []
    for raw in WIKILINK_RE.findall(clean):
        target = raw.strip()
        if Path(target).suffix.lower() in NON_NOTE_EXT:
            continue
        links.append(target)

    stat = path.stat()
    return {
        "path": path.relative_to(root).as_posix(),
        "title": str(fm.get("title") or path.stem),
        "stem": path.stem,
        "frontmatter": fm,
        "has_frontmatter": bool(fm),
        "tags": sorted(set(tags)),
        "links": sorted(set(links)),
        "headings": [h.strip() for h in HEADING_RE.findall(clean)][:30],
        "words": len(clean.split()),
        "modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(timespec="seconds"),
    }


def iter_note_files(root: Path, ignore: list[str]):
    ignore_names = {i.strip("/") for i in ignore if "/" not in i.strip("/")}
    ignore_paths = {i.strip("/") for i in ignore if "/" in i.strip("/")}
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = Path(dirpath).relative_to(root).as_posix()
        dirnames[:] = [
            d for d in dirnames
            if d not in ignore_names
            and (f"{rel_dir}/{d}" if rel_dir != "." else d) not in ignore_paths
        ]
        for fn in filenames:
            if fn.endswith(".md"):
                yield Path(dirpath) / fn


# --------------------------------------------------------------------------- index
def build_index(repos: list[dict]) -> dict:
    notes: list[dict] = []
    repo_meta: dict = {}
    for r in repos:
        root: Path = r["path"]
        if not root.is_dir():
            repo_meta[r["name"]] = {"path": str(root), "error": "path not found"}
            continue
        cfg = load_repo_config(root)
        count = 0
        for f in iter_note_files(root, cfg["repo"]["ignore"]):
            n = parse_note(f, root)
            n["repo"] = r["name"]
            n["id"] = f'{r["name"]}:{n["path"]}'
            notes.append(n)
            count += 1
        repo_meta[r["name"]] = {"path": str(root), "notes": count}

    # resolve links -> note ids (same repo first, then any repo)
    by_repo_stem: dict = {}
    by_stem: dict = {}
    for n in notes:
        by_repo_stem.setdefault((n["repo"], n["stem"].lower()), []).append(n["id"])
        by_stem.setdefault(n["stem"].lower(), []).append(n["id"])
    backlinks: dict = {n["id"]: [] for n in notes}
    for n in notes:
        resolved, broken = [], []
        for target in n["links"]:
            stem = Path(target).stem.lower() if target.lower().endswith(".md") else Path(target).name.lower()
            hit = by_repo_stem.get((n["repo"], stem)) or by_stem.get(stem)
            if hit:
                resolved.append(hit[0])
                backlinks[hit[0]].append(n["id"])
            else:
                broken.append(target)
        n["resolved_links"] = resolved
        n["broken_links"] = broken
    for n in notes:
        n["backlinks"] = sorted(set(backlinks[n["id"]]))

    return {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "repos": repo_meta,
        "notes": notes,
    }


def save_index(index: dict) -> Path:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_FILE.write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
    return INDEX_FILE


def load_index(max_age_hours: float = 24, rebuild: bool = False) -> dict:
    """Load cached index, rebuilding it if missing, stale, or for different repos."""
    import time

    repos = load_registry()
    stale = not INDEX_FILE.exists()
    cached = {}
    if not stale:
        try:
            cached = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            stale = True
    if not stale:
        cached_repos = cached.get("repos", {})
        current_repos = {r["name"]: str(r["path"]) for r in repos}
        cached_paths = {name: meta.get("path") for name, meta in cached_repos.items()} if isinstance(cached_repos, dict) else {}
        stale = (
            current_repos != cached_paths
            or (time.time() - INDEX_FILE.stat().st_mtime) > max_age_hours * 3600
        )
    if rebuild or stale:
        idx = build_index(repos)
        save_index(idx)
        return idx
    return cached
