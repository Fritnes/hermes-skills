#!/usr/bin/env python3
"""Build the cross-repo note index at ~/.hermes/vault/index.json.

Usage: build_index.py [--repo NAME]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from vaultlib import build_index, save_index, select_repos  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", help="index only this repo (still overwrites the whole index file)")
    a = ap.parse_args()

    idx = build_index(select_repos(a.repo))
    out = save_index(idx)
    print(f"Index written: {out}")
    for name, meta in idx["repos"].items():
        print(f"  {name:<15} {meta.get('notes', 0):>5} notes" + (f"  ERROR: {meta['error']}" if "error" in meta else ""))
    broken = sum(len(n["broken_links"]) for n in idx["notes"])
    print(f"Total: {len(idx['notes'])} notes, {broken} broken links")


if __name__ == "__main__":
    main()
