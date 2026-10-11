#!/usr/bin/env python3
"""Shared helpers for the Obsidian vault skills (stdlib only, Python 3.11+).

Config locations
  Global registry : ~/.hermes/vault/repos.toml      (which repos exist, where)
  Per-repo config : <repo>/.vault.toml              (conventions for that repo)
  Index cache     : ~/.hermes/vault/index.json      (generated, safe to delete)

Override the global dir with the HERMES_VAULT_DIR environment variable.
"""
from __future__ import annotations

import copy
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    sys.exit("Python 3.11+ is required (needs the stdlib 'tomllib' module).")

CONFIG_DIR = Path(os.environ.get("HERMES_VAULT_DIR", "~/.hermes/vault")).expanduser()
REGISTRY = CONFIG_DIR / "repos.toml"
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


def load_registry() -> list[dict]:
    if not REGISTRY.exists():
        sys.exit(
            f"NOT CONFIGURED: no registry at {REGISTRY}.\n"
            f"Run first-time setup: ask the user for their vault repos, then use\n"
            f"  vault_config.py detect --path <p>   and   vault_config.py add-repo --name <n> --path <p>"
        )
    data = tomllib.loads(REGISTRY.read_text(encoding="utf-8"))
    repos = []
    for r in data.get("repos", []):
        if not r.get("enabled", True):
            continue
        repos.append(
            {
                "name": r["name"],
                "path": Path(r["path"]).expanduser(),
                "branch": r.get("branch", "main"),
                "remote": r.get("remote", "origin"),
            }
        )
    if not repos:
        sys.exit(f"NOT CONFIGURED: no enabled repos in {REGISTRY}. Use vault_config.py add-repo.")
    return repos


def select_repos(name: str | None) -> list[dict]:
    repos = load_registry()
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
    """Load cached index, rebuilding it if missing, stale, or rebuild=True."""
    import time

    stale = (
        not INDEX_FILE.exists()
        or (time.time() - INDEX_FILE.stat().st_mtime) > max_age_hours * 3600
    )
    if rebuild or stale:
        idx = build_index(load_registry())
        save_index(idx)
        return idx
    return json.loads(INDEX_FILE.read_text(encoding="utf-8"))
