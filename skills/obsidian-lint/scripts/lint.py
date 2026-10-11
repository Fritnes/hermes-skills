#!/usr/bin/env python3
"""Lint vault notes across repos (read-only; never modifies files).

Usage: lint.py [--repo NAME] [--check broken,orphans,frontmatter,duplicates,empty] [--limit N]

Checks
  broken       [[wikilinks]] that resolve to no note in any repo
  orphans      notes with no backlinks (ignores folders in [lint].orphan_ignore_folders)
  frontmatter  notes missing frontmatter or keys in [lint].required_keys
  duplicates   same note title/filename used more than once
  empty        notes with fewer than 5 words
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from vaultlib import build_index, load_registry, load_repo_config, save_index  # noqa: E402

ALL = ["broken", "orphans", "frontmatter", "duplicates", "empty"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo")
    ap.add_argument("--check", default=",".join(ALL))
    ap.add_argument("--limit", type=int, default=20, help="max findings shown per check")
    a = ap.parse_args()

    checks = [c.strip() for c in a.check.split(",") if c.strip()]
    bad = [c for c in checks if c not in ALL]
    if bad:
        sys.exit(f"Unknown check(s): {bad}. Valid: {ALL}")

    registry = load_registry()
    idx = build_index(registry)  # always fresh so results reflect the current files
    save_index(idx)
    cfgs = {r["name"]: load_repo_config(r["path"]) for r in registry if r["path"].is_dir()}
    notes = [n for n in idx["notes"] if not a.repo or n["repo"] == a.repo]

    findings: dict[str, list[str]] = defaultdict(list)
    for n in notes:
        cfg = cfgs[n["repo"]]
        top = n["path"].split("/")[0]
        if "broken" in checks:
            for t in n["broken_links"]:
                findings["broken"].append(f"{n['id']}  ->  [[{t}]]")
        if "orphans" in checks and not n["backlinks"] and top not in cfg["lint"]["orphan_ignore_folders"]:
            findings["orphans"].append(n["id"])
        if "frontmatter" in checks and top != cfg["repo"]["templates_dir"]:
            if not n["has_frontmatter"]:
                findings["frontmatter"].append(f"{n['id']}  (no frontmatter)")
            else:
                missing = [k for k in cfg["lint"]["required_keys"] if not n["frontmatter"].get(k)]
                if missing:
                    findings["frontmatter"].append(f"{n['id']}  (missing: {', '.join(missing)})")
        if "empty" in checks and n["words"] < 5 and top != cfg["repo"]["templates_dir"]:
            findings["empty"].append(f"{n['id']}  ({n['words']} words)")
    if "duplicates" in checks:
        seen = defaultdict(list)
        for n in notes:
            seen[n["stem"].lower()].append(n["id"])
        for stem, ids in seen.items():
            if len(ids) > 1:
                findings["duplicates"].append(f"'{stem}': " + ", ".join(ids))

    total = 0
    for c in checks:
        items = findings.get(c, [])
        total += len(items)
        print(f"\n## {c}: {len(items)}")
        for line in items[: a.limit]:
            print(f"  {line}")
        if len(items) > a.limit:
            print(f"  ... and {len(items) - a.limit} more (raise --limit)")
    print(f"\nScanned {len(notes)} notes, {total} finding(s).")


if __name__ == "__main__":
    main()
