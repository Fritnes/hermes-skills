---
name: obsidian-lint
description: Health-check my vaults - broken wikilinks, orphan notes, missing frontmatter, duplicate titles, empty notes. Use when I ask to audit, clean up, or check my notes. Also handles first-time registration of my vault repos through chat.
version: 2.0.0
---

# Obsidian Lint

Read-only audit across all repos.

## First-time setup (done in chat, before the task)
Config is created by talking to me. Never ask me to edit files by hand, and never edit `repos.toml` / `.vault.toml` yourself; use `vault_config.py`.

1. Run: `python ~/.hermes/skills/obsidian-lint/scripts/vault_config.py status`
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

## Settings to ask about (section `lint` in `<repo>/.vault.toml`)
- **Required frontmatter keys** (default `tags`). Use the "Common frontmatter keys" from `detect` to suggest -> `init-repo --name X --required-keys "title,type,tags"`
- **Folders where orphan notes are fine** (default `daily, templates, inbox`) -> `--orphan-ignore "daily,templates,inbox"`

## Script
`python ~/.hermes/skills/obsidian-lint/scripts/lint.py [--repo X] [--check broken,orphans,frontmatter,duplicates,empty] [--limit N]`

## Workflow
1. Run the lint (all checks, or only what I asked for).
2. Summarize: counts per check, then the 5 most important findings.
3. Propose fixes grouped by type. Wait for my approval before changing ANY file.
4. Apply approved fixes one repo at a time; suggest obsidian-sync to commit.

## Rules
- The script never modifies files; you must not either without approval.
- Never delete notes. For orphans/duplicates suggest linking or merging; I decide.
