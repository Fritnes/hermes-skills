---
name: obsidian-index
description: Build and query a searchable index of all notes across my vault repos (titles, tags, links, backlinks). Use when I ask to find notes, list by tag, show backlinks, or summarize a topic across vaults. Also handles first-time registration of my vault repos through chat.
version: 2.0.0
---

# Obsidian Index

A cached JSON index of every note in every repo, so you search metadata instead of reading files.

## First-time setup (done in chat, before the task)
Config is created by talking to me. Never ask me to edit files by hand, and never edit `repos.toml` / `.vault.toml` yourself; use `vault_config.py`.

1. Run: `python ~/.hermes/skills/obsidian-index/scripts/vault_config.py status`
   (if the path is wrong: `find ~/.hermes/skills -name vault_config.py`)
2. **No repos registered, or the repo I mention is missing?** Ask me for each vault repo: a short name and its local folder path
   (or its git URL plus where to clone it). One question at a time. Then:
   - `vault_config.py detect --path <path>` and show me a short summary of what you found
   - `vault_config.py add-repo --name <n> --path <path> [--url <git-url>]`
3. **This skill's settings not yet configured?** (see "Settings to ask about" below; `status` lists missing sections)
   Propose defaults based on `detect`, ask me to confirm or change them, then save with `vault_config.py init-repo`.
   Ask only about what `detect` could not tell you. If I say "just use defaults", proceed without saving.
4. Tell me in one line what was saved, then do the actual task.
Setup runs once per repo. Skip steps already done.

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
