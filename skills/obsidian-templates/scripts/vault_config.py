#!/usr/bin/env python3
"""Config tool for the Obsidian vault skills. Hermes runs this during chat-based setup,
so nobody has to edit TOML by hand.

Commands
  status                                   what is configured / missing (run this first)
  detect --path P                          inspect a folder: git, Obsidian settings, folders, frontmatter keys
  add-repo --name N --path P [--branch B] [--remote R] [--url U]   register a repo (clones from --url if P missing)
  remove-repo --name N                     unregister (never deletes files)
  init-repo --name N [options]             create/update <repo>/.vault.toml (only the options you pass)
        --type T  --templates-dir D  --ignore a,b  --commit-prefix P  --auto-push true|false
        --required-keys a,b  --orphan-ignore a,b
        --folder TYPE=PATH (repeatable)  --naming TYPE=PATTERN (repeatable)
  show --name N                            print the repo's .vault.toml
  conventions show|set|append              read / write ~/.hermes/vault/conventions.md (text via stdin)

Files
  ~/.hermes/vault/repos.toml      global registry
  <repo>/.vault.toml              per-repo settings
  ~/.hermes/vault/conventions.md  writing conventions (tags, frontmatter, linking)
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import vaultlib as V  # noqa: E402

tomllib = V.tomllib


# ----------------------------------------------------------------- tiny TOML writer
def _q(s: str) -> str:
    return json.dumps(s, ensure_ascii=False)


def _key(k: str) -> str:
    return k if re.fullmatch(r"[A-Za-z0-9_-]+", k) else _q(k)


def _val(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, list):
        return "[" + ", ".join(_val(x) for x in v) + "]"
    return _q(str(v))


def dumps(data: dict) -> str:
    out: list[str] = []
    for k, v in data.items():
        if not isinstance(v, (dict, list)) or (isinstance(v, list) and not (v and isinstance(v[0], dict))):
            out.append(f"{_key(k)} = {_val(v)}")
    for k, v in data.items():
        if isinstance(v, dict):
            out.append(f"\n[{_key(k)}]")
            out += [f"{_key(a)} = {_val(b)}" for a, b in v.items()]
        elif isinstance(v, list) and v and isinstance(v[0], dict):
            for item in v:
                out.append(f"\n[[{_key(k)}]]")
                out += [f"{_key(a)} = {_val(b)}" for a, b in item.items()]
    return "\n".join(out).strip() + "\n"


# ----------------------------------------------------------------- helpers
def read_raw_registry() -> dict:
    if V.REGISTRY.exists():
        return tomllib.loads(V.REGISTRY.read_text(encoding="utf-8"))
    return {"repos": []}


def write_registry(data: dict) -> None:
    V.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    V.REGISTRY.write_text(
        "# Managed by vault_config.py (Hermes edits this through chat). Safe to edit by hand too.\n\n" + dumps(data),
        encoding="utf-8",
    )


def git(path: Path, *args: str, timeout: int = 20) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(path), *args], capture_output=True, text=True, timeout=timeout)


def read_json(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def find_repo(name: str) -> dict:
    for r in read_raw_registry().get("repos", []):
        if r["name"] == name:
            return r
    sys.exit(f"Unknown repo '{name}'. Registered: {[r['name'] for r in read_raw_registry().get('repos', [])]}")


# ----------------------------------------------------------------- commands
def cmd_status(_a):
    print(f"Config dir : {V.CONFIG_DIR}")
    repos = read_raw_registry().get("repos", [])
    if not V.REGISTRY.exists() or not repos:
        print("Registry   : NOT CONFIGURED (no repos registered)")
        print("=> Run first-time setup: ask the user for each vault repo's name and path/URL.")
    else:
        print(f"Registry   : {V.REGISTRY}  ({len(repos)} repo(s))")
    for r in repos:
        p = Path(r["path"]).expanduser()
        exists = p.is_dir()
        is_git = exists and git(p, "rev-parse", "--is-inside-work-tree").returncode == 0
        cfgf = p / V.REPO_CONFIG_NAME
        sections = sorted(tomllib.loads(cfgf.read_text(encoding="utf-8")).keys()) if cfgf.exists() else []
        print(f"- {r['name']}: path={r['path']} exists={'yes' if exists else 'NO'} git={'yes' if is_git else 'no'}"
              f"{' enabled=false' if r.get('enabled') is False else ''}")
        print(f"    .vault.toml sections set: {', '.join(sections) if sections else '(none; defaults in use)'}")
        missing = [s for s in ("folders", "naming", "lint", "sync", "repo") if s not in sections]
        if missing:
            print(f"    not yet configured: {', '.join(missing)}")
    conv = V.CONVENTIONS_FILE
    print(f"Conventions: {'set (' + str(conv) + ')' if conv.exists() and conv.read_text().strip() else 'NOT SET'}")


def cmd_detect(a):
    p = Path(a.path).expanduser()
    if not p.is_dir():
        print(f"Path does not exist: {p}")
        return
    print(f"Path: {p}")
    if git(p, "rev-parse", "--is-inside-work-tree").returncode == 0:
        branch = git(p, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
        remote = git(p, "remote", "get-url", "origin").stdout.strip() or "(no origin remote)"
        dirty = len([l for l in git(p, "status", "--porcelain").stdout.splitlines() if l.strip()])
        print(f"Git: yes, branch={branch}, origin={remote}, uncommitted files={dirty}")
    else:
        print("Git: NOT a git repository")

    obs = p / ".obsidian"
    print(f"Obsidian vault (.obsidian present): {'yes' if obs.is_dir() else 'no'}")
    tpl = read_json(obs / "templates.json").get("folder")
    tpr = read_json(obs / "plugins" / "templater-obsidian" / "data.json").get("templates_folder")
    dn = read_json(obs / "daily-notes.json")
    if tpl:
        print(f"Templates folder (core Templates plugin): {tpl}")
    if tpr:
        print(f"Templates folder (Templater plugin): {tpr}")
    if not (tpl or tpr):
        guess = next((d.name for d in p.iterdir() if d.is_dir() and d.name.lower() in ("templates", "template", "_templates")), None)
        print(f"Templates folder: not set in Obsidian; guess={guess or 'none found'}")
    if dn:
        print(f"Daily notes plugin: folder={dn.get('folder') or '(root)'} format={dn.get('format', 'YYYY-MM-DD')}")

    tops = sorted(d.name for d in p.iterdir() if d.is_dir() and not d.name.startswith("."))
    print(f"Top-level folders: {', '.join(tops) or '(none)'}")

    files = list(V.iter_note_files(p, V.DEFAULTS["repo"]["ignore"]))
    print(f"Markdown notes: {len(files)}")
    keys, tags = Counter(), Counter()
    for f in files[:300]:
        n = V.parse_note(f, p)
        keys.update(n["frontmatter"].keys())
        tags.update(n["tags"])
    if keys:
        print("Common frontmatter keys: " + ", ".join(f"{k}({c})" for k, c in keys.most_common(8)))
    if tags:
        print("Common tags: " + ", ".join(f"#{k}({c})" for k, c in tags.most_common(10)))
    print("\nUse this to PROPOSE settings to the user; do not ask what is already visible above.")


def cmd_add_repo(a):
    p = Path(a.path).expanduser()
    if not p.exists():
        if not a.url:
            sys.exit(f"{p} does not exist. Give --url to clone it there, or fix the path.")
        p.parent.mkdir(parents=True, exist_ok=True)
        c = subprocess.run(["git", "clone", a.url, str(p)], capture_output=True, text=True, timeout=600)
        if c.returncode != 0:
            sys.exit(f"git clone failed:\n{c.stderr.strip()[:500]}")
        print(f"Cloned {a.url} -> {p}")
    is_git = git(p, "rev-parse", "--is-inside-work-tree").returncode == 0
    branch = a.branch or (git(p, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip() if is_git else "main") or "main"

    data = read_raw_registry()
    repos = data.setdefault("repos", [])
    if any(r["name"] == a.name for r in repos):
        sys.exit(f"A repo named '{a.name}' already exists. Pick another name or remove it first.")
    repos.append({"name": a.name, "path": a.path, "branch": branch, "remote": a.remote})
    write_registry(data)
    print(f"Registered '{a.name}' -> {a.path} (branch {branch}, remote {a.remote})")
    if not is_git:
        print("WARNING: not a git repository; obsidian-sync will report an error for it.")


def cmd_remove_repo(a):
    data = read_raw_registry()
    before = len(data.get("repos", []))
    data["repos"] = [r for r in data.get("repos", []) if r["name"] != a.name]
    if len(data["repos"]) == before:
        sys.exit(f"No repo named '{a.name}'.")
    write_registry(data)
    print(f"Unregistered '{a.name}'. Files on disk were NOT touched.")


def _csv(s: str) -> list[str]:
    return [x.strip() for x in s.split(",") if x.strip()]


def _pairs(items: list[str] | None, label: str) -> dict:
    out = {}
    for it in items or []:
        if "=" not in it:
            sys.exit(f"--{label} expects TYPE=VALUE, got '{it}'")
        k, v = it.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def cmd_init_repo(a):
    r = find_repo(a.name)
    p = Path(r["path"]).expanduser()
    if not p.is_dir():
        sys.exit(f"Repo path not found: {p}")
    f = p / V.REPO_CONFIG_NAME
    data = tomllib.loads(f.read_text(encoding="utf-8")) if f.exists() else {}

    def put(section, key, value):
        data.setdefault(section, {})[key] = value

    if a.type: put("repo", "type", a.type)
    if a.templates_dir: put("repo", "templates_dir", a.templates_dir)
    if a.ignore is not None: put("repo", "ignore", _csv(a.ignore))
    if a.commit_prefix: put("sync", "commit_prefix", a.commit_prefix)
    if a.auto_push is not None: put("sync", "auto_push", a.auto_push.lower() == "true")
    if a.required_keys is not None: put("lint", "required_keys", _csv(a.required_keys))
    if a.orphan_ignore is not None: put("lint", "orphan_ignore_folders", _csv(a.orphan_ignore))
    for k, v in _pairs(a.folder, "folder").items(): put("folders", k, v)
    for k, v in _pairs(a.naming, "naming").items(): put("naming", k, v)

    f.write_text("# Managed by vault_config.py. Commit this file with the repo.\n\n" + dumps(data), encoding="utf-8")
    print(f"Wrote {f}\n")
    print(f.read_text(encoding="utf-8"))
    print("Note: .vault.toml is a new/changed file in the repo; commit it with obsidian-sync when ready.")


def cmd_show(a):
    p = Path(find_repo(a.name)["path"]).expanduser() / V.REPO_CONFIG_NAME
    print(p.read_text(encoding="utf-8") if p.exists() else "(no .vault.toml yet; built-in defaults are used)")


def cmd_conventions(a):
    f = V.CONVENTIONS_FILE
    if a.action == "show":
        print(f.read_text(encoding="utf-8") if f.exists() else "(no conventions set yet)")
        return
    text = sys.stdin.read()
    if not text.strip():
        sys.exit("No text on stdin. Pipe the conventions text in (e.g. with a heredoc).")
    V.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if a.action == "set":
        f.write_text(text.rstrip() + "\n", encoding="utf-8")
    else:
        old = f.read_text(encoding="utf-8").rstrip() + "\n\n" if f.exists() else ""
        f.write_text(old + text.rstrip() + "\n", encoding="utf-8")
    print(f"Saved {f}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    s = sub.add_parser("detect"); s.add_argument("--path", required=True); s.set_defaults(fn=cmd_detect)
    s = sub.add_parser("add-repo")
    s.add_argument("--name", required=True); s.add_argument("--path", required=True)
    s.add_argument("--branch"); s.add_argument("--remote", default="origin"); s.add_argument("--url")
    s.set_defaults(fn=cmd_add_repo)
    s = sub.add_parser("remove-repo"); s.add_argument("--name", required=True); s.set_defaults(fn=cmd_remove_repo)
    s = sub.add_parser("init-repo")
    s.add_argument("--name", required=True)
    for opt in ("--type", "--templates-dir", "--ignore", "--commit-prefix", "--auto-push", "--required-keys", "--orphan-ignore"):
        s.add_argument(opt)
    s.add_argument("--folder", action="append"); s.add_argument("--naming", action="append")
    s.set_defaults(fn=cmd_init_repo)
    s = sub.add_parser("show"); s.add_argument("--name", required=True); s.set_defaults(fn=cmd_show)
    s = sub.add_parser("conventions"); s.add_argument("action", choices=["show", "set", "append"]); s.set_defaults(fn=cmd_conventions)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
