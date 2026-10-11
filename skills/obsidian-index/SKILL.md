---
name: obsidian-index
description: Build and query a searchable index of notes in repos registered with git-repo-sync (titles, tags, links, backlinks). Use when I ask to find notes, list by tag, show backlinks, or summarize a topic across vaults.
version: 2.0.0
---

# Obsidian Index

A cached JSON index of every note in every repo, so you search metadata instead of reading files.

## Repo selection and first use

Repository names and local paths come from `~/.hermes/git-repos.toml`, managed by `git-repo-sync`. Default index operations include repos marked `obsidian = true` or containing `.obsidian/` or `.vault.toml`. If the requested repo is not registered or cloned, use `git-repo-sync` to set it up; do not create another repo registry.

Use `--repo <name>` to target one registered repo. Obsidian-specific ignore settings live in that repo's `.vault.toml`; inspect the vault first and ask before saving changes with `vault_config.py init-repo`.

## Settings to ask about (section `repo` in `<repo>/.vault.toml`)
- Folders to exclude from the index (default: `.obsidian, .git, .trash, attachments, node_modules`).
  Ask whether there are others (archive, private, imported...) -> `init-repo --name X --ignore ".obsidian,.git,.trash,attachments,archive"`
  (`--ignore` REPLACES the list, so always include the defaults you want to keep.)

## Scripts (`~/.hermes/skills/obsidian-index/scripts/`)
- `build_index.py [--repo X]` rebuild the index (`~/.hermes/vault/index.json`)
- `search_index.py` query it:
  - `--q "words"` title/path/headings/tags; `--tag project/alpha` (prefix match)
  - `--backlinks "Note"` / `--links "Note"`; `--recent 15`; `--stats`
  - filters: `--repo X --limit N --json --rebuild`

## Workflow
1. Search the index first. Do NOT grep or open files for discovery.
2. Open full note files only for the few top matches you need.
3. Index auto-rebuilds if older than 24h; use `--rebuild` after a sync or after notes were created.
4. Cite results as `[[Note Title]]` + repo (the `id` field is `repo:path`).

## Rules
- Read-only: never modify notes.
- If a repo shows `path not found`, tell me; do not guess another path.
