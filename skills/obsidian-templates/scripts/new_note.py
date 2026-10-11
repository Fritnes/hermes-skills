#!/usr/bin/env python3
"""Create a note from a template, in the right repo/folder, never overwriting.

Usage:
  new_note.py --repo NAME --type TYPE --title "Title" [--tags a,b] [--date YYYY-MM-DD] [--dry-run]
  new_note.py --repo NAME --list        show available note types and template sources

Template lookup order for TYPE:
  1. <repo>/<templates_dir>/<TYPE>.md   (your real Obsidian templates; wins)
  2. ../templates/<TYPE>.md             (fallback bundled with this skill)

Placeholders: {{title}} {{date}} {{time}} {{date:YYYY-MM-DD}} {{time:HH:mm}} {{tags}} {{repo}}
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from vaultlib import load_repo_config, select_repos  # noqa: E402

SKILL_TEMPLATES = Path(__file__).resolve().parent.parent / "templates"
TOKENS = {
    "YYYY": "%Y", "YY": "%y", "MM": "%m", "DD": "%d", "HH": "%H",
    "mm": "%M", "ss": "%S", "dddd": "%A", "ddd": "%a",
}
TOKEN_RE = re.compile("|".join(sorted(TOKENS, key=len, reverse=True)))
BAD_CHARS = re.compile(r'[\\/:*?"<>|#^\[\]]')


def fmt_date(dt: datetime, pattern: str) -> str:
    return TOKEN_RE.sub(lambda m: dt.strftime(TOKENS[m.group(0)]), pattern)


def find_template(repo_path: Path, cfg: dict, note_type: str) -> Path | None:
    candidates = []
    tdir = repo_path / cfg["repo"]["templates_dir"]
    if tdir.is_dir():
        candidates += [p for p in tdir.glob("*.md") if p.stem.lower() == note_type.lower()]
    candidates += [p for p in SKILL_TEMPLATES.glob("*.md") if p.stem.lower() == note_type.lower()]
    return candidates[0] if candidates else None


def render(text: str, *, title: str, now: datetime, tags: list[str], repo: str) -> str:
    def sub(m: re.Match) -> str:
        key, _, pattern = m.group(1).partition(":")
        key = key.strip().lower()
        if key == "title":
            return title
        if key == "date":
            return fmt_date(now, pattern or "YYYY-MM-DD")
        if key == "time":
            return fmt_date(now, pattern or "HH:mm")
        if key == "tags":
            return ", ".join(tags)
        if key == "repo":
            return repo
        return m.group(0)  # unknown placeholder: leave untouched

    out = re.sub(r"\{\{\s*([^}]+?)\s*\}\}", sub, text)
    # tidy empty tag slots in frontmatter lists: [idea, ] -> [idea]
    def tidy(m: re.Match) -> str:
        inner = ", ".join(x.strip() for x in m.group(2).split(",") if x.strip())
        return f"{m.group(1)}[{inner}]"
    return re.sub(r"^(tags:\s*)\[(.*?)\]\s*$", tidy, out, flags=re.M)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--type")
    ap.add_argument("--title")
    ap.add_argument("--tags", default="")
    ap.add_argument("--date", help="YYYY-MM-DD (default: today)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()

    repo = select_repos(a.repo)[0]
    root: Path = repo["path"]
    if not root.is_dir():
        sys.exit(f"Repo path not found: {root}")
    cfg = load_repo_config(root)

    if a.list:
        types = set(cfg["folders"]) | {p.stem for p in SKILL_TEMPLATES.glob("*.md")}
        tdir = root / cfg["repo"]["templates_dir"]
        if tdir.is_dir():
            types |= {p.stem for p in tdir.glob("*.md")}
        for t in sorted(types):
            tpl = find_template(root, cfg, t)
            print(f"{t:<12} folder={cfg['folders'].get(t, cfg['folders']['inbox']):<12} template={tpl or 'MISSING'}")
        return

    if not (a.type and a.title):
        sys.exit("--type and --title are required (or use --list)")

    tpl = find_template(root, cfg, a.type)
    if not tpl:
        sys.exit(f"No template for type '{a.type}'. Run with --list to see available types.")

    now = datetime.strptime(a.date, "%Y-%m-%d") if a.date else datetime.now()
    if a.date:
        now = now.replace(hour=datetime.now().hour, minute=datetime.now().minute)
    tags = [t.strip().lstrip("#") for t in a.tags.split(",") if t.strip()]

    folder = cfg["folders"].get(a.type, cfg["folders"]["inbox"])
    name_pat = cfg["naming"].get(a.type, "{title}")
    filename = name_pat.format(date=now.strftime("%Y-%m-%d"), title=a.title)
    filename = BAD_CHARS.sub("-", filename).strip() + ".md"
    target = root / folder / filename

    content = render(tpl.read_text(encoding="utf-8"), title=a.title, now=now, tags=tags, repo=repo["name"])

    if a.dry_run:
        print(f"[dry-run] would create: {target}\n[template: {tpl}]\n---\n{content}")
        return
    if target.exists():
        sys.exit(f"REFUSED: {target} already exists (never overwriting). Append manually or pick another title.")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    print(f"Created: {target}")
    print(f"Repo: {repo['name']}  (not committed; use obsidian-sync to commit)")


if __name__ == "__main__":
    main()
