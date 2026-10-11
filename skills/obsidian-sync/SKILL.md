---
name: obsidian-sync
description: Pull, status-check, commit and push my Obsidian vault git repos safely. Use when I ask to sync, update, back up, or check the state of my notes. Also handles first-time registration of my vault repos through chat.
version: 2.0.0
---

# Obsidian Sync

Manage the git repos that hold my Obsidian vaults.

## First-time setup (done in chat, before the task)
Config is created by talking to me. Never ask me to edit files by hand, and never edit `repos.toml` / `.vault.toml` yourself; use `vault_config.py`.

1. Run: `python ~/.hermes/skills/obsidian-sync/scripts/vault_config.py status`
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

## Settings to ask about (section `sync` in `<repo>/.vault.toml`)
- Commit message prefix (default `notes`) -> `init-repo --name X --commit-prefix notes`
- Whether pushing may ever be automatic (default: no, always ask) -> `--auto-push false`

## Script
`python ~/.hermes/skills/obsidian-sync/scripts/vault_sync.py <command>`

| Command | What it does |
|---|---|
| `status [--repo X] [--no-fetch]` | table: branch, ahead/behind, clean/dirty |
| `diff [--repo X]` | list changed files per repo |
| `pull [--repo X]` | `pull --rebase`; skips dirty repos; aborts on conflict |
| `commit --repo X [-m "msg"]` | stage all + commit with the prefix |
| `push --repo X` | push (one repo at a time) |

## Workflow
1. Run `status`; show me the table.
2. `pull` clean repos. Report any SKIPPED/CONFLICT lines verbatim.
3. For dirty repos: run `diff`, summarize the changes, ask before committing.
4. Propose a short commit message. Commit only after I approve. Push only after I separately approve.
5. End with the `status` table.

## Rules
- NEVER force-push, reset --hard, or resolve merge conflicts yourself. Stop and report the file.
- `commit` and `push` are single-repo on purpose; never loop them silently over all repos.
- One repo failing must not stop the others.
