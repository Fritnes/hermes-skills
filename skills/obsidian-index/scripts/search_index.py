#!/usr/bin/env python3
"""Query the vault index without opening note files.

Usage:
  search_index.py --q "text"            match title / path / headings / tags (all words must match)
  search_index.py --tag project/alpha   notes with this tag (prefix match: 'project' matches 'project/alpha')
  search_index.py --backlinks "Note"    notes linking to a note
  search_index.py --links "Note"        notes a note links to
  search_index.py --recent 15           most recently modified
  search_index.py --stats               counts per repo / top tags
Filters: --repo NAME  --limit N  --json  --rebuild
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from vaultlib import load_index  # noqa: E402


def find_note(notes, ref: str):
    r = ref.lower()
    exact = [n for n in notes if n["id"].lower() == r or n["stem"].lower() == r or n["title"].lower() == r]
    return exact or [n for n in notes if r in n["title"].lower()]


def fmt(n) -> str:
    tags = " ".join(f"#{t}" for t in n["tags"][:6])
    return f"{n['id']}  |  {n['title']}  |  {tags}  |  {n['modified'][:10]}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--q")
    ap.add_argument("--tag")
    ap.add_argument("--backlinks")
    ap.add_argument("--links")
    ap.add_argument("--recent", type=int)
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--repo")
    ap.add_argument("--limit", type=int, default=25)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--rebuild", action="store_true")
    a = ap.parse_args()

    idx = load_index(rebuild=a.rebuild)
    notes = [n for n in idx["notes"] if not a.repo or n["repo"] == a.repo]
    by_id = {n["id"]: n for n in idx["notes"]}

    if a.stats:
        print(f"Index generated: {idx['generated']}")
        for name, meta in idx["repos"].items():
            print(f"  {name:<15} {meta.get('notes', 0)} notes")
        top = Counter(t for n in notes for t in n["tags"]).most_common(15)
        print("Top tags: " + ", ".join(f"#{t}({c})" for t, c in top))
        return

    result = notes
    if a.q:
        words = a.q.lower().split()
        def hay(n):
            return " ".join([n["title"], n["path"], " ".join(n["headings"]), " ".join(n["tags"])]).lower()
        result = [n for n in result if all(w in hay(n) for w in words)]
    if a.tag:
        t = a.tag.lstrip("#").lower()
        result = [n for n in result if any(x.lower() == t or x.lower().startswith(t + "/") for x in n["tags"])]
    if a.backlinks or a.links:
        ref = a.backlinks or a.links
        targets = find_note(idx["notes"], ref)
        if not targets:
            sys.exit(f"No note matches '{ref}'")
        ids = set()
        for tgt in targets:
            ids |= set(tgt["backlinks"] if a.backlinks else tgt["resolved_links"])
        result = [by_id[i] for i in ids if i in by_id]
    if a.recent:
        result = sorted(result, key=lambda n: n["modified"], reverse=True)[: a.recent]
    elif not (a.q or a.tag or a.backlinks or a.links):
        ap.print_help()
        return

    result = result[: a.limit]
    if a.json:
        slim = [{k: n[k] for k in ("id", "title", "tags", "modified", "headings", "broken_links")} for n in result]
        print(json.dumps(slim, ensure_ascii=False, indent=2))
    else:
        print("\n".join(fmt(n) for n in result) or "(no results)")
        print(f"-- {len(result)} result(s)")


if __name__ == "__main__":
    main()
