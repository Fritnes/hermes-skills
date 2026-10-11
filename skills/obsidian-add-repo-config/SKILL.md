---
name: obsidian-add-repo-config
description: Add, update, disable, and remove Obsidian vault repo configuration. Use when I say I have a new vault, connect my repo, change my folder settings, move a repo, pause a repo, or remove a repo from my setup.
version: 2.0.0
---

# Obsidian Add Repo Config

This skill owns the full repo-config lifecycle for Obsidian vaults. It is the dedicated setup skill for adding and managing vault repo configuration, even when the other Obsidian skills also have their own built-in setup flow.

## Primary responsibilities

- Add a repo and register it in the shared Hermes vault config.
- Update repo settings without disturbing the rest of the configuration.
- Move a repo when the local path changes.
- Disable or re-enable a repo without deleting its files.
- Remove a repo cleanly from the registry without deleting the vault contents.
- Validate repo config before it is used by the other skills.

## First-time setup / workflow

1. Ask for the repo name and either its local path or git URL.
2. If the repo is not on disk, ask whether to clone it and then clone it.
3. Run config detection on the repo path and inspect its Obsidian settings, templates folder, common frontmatter keys, and likely note structure.
4. Show one combined proposal for the repo config, including:
   - templates folder
   - note-type folders
   - filename patterns
   - lint rules
   - commit prefix
5. Ask for confirmation before saving.
6. Save the repo config in one step and run validation.
7. Report the result clearly: created, updated, disabled, re-enabled, or removed.

## Commands to use

Use the config tool commands below as needed:

- `vault_config.py add-repo --name <n> --path <path> [--url <git-url>]`
- `vault_config.py update-repo --name <n> [--path <path>] [--url <git-url>]`
- `vault_config.py toggle-repo --name <n> --enabled true|false`
- `vault_config.py validate --repo <n>`
- `vault_config.py status`

## Validation rules

Run `validate` before finishing the flow. Report all of the following clearly:

- Problems:
  - repo path does not exist
  - folder is not a git repo
  - invalid TOML
- Warnings:
  - missing remote
  - missing templates folder
- Naming pattern issues:
  - only `{date}` and `{title}` are supported
  - anything else, such as `{weekday}`, is invalid because the note-creation scripts cannot fill it

## Update behavior

- Only update the fields the user names.
- Keep all other repo settings intact.
- If the repo path moved, update the path and re-run validation.
- If the repo is paused, skip it in other skills without losing configuration.
- If the repo is removed, unregister it only; do not delete files.

## Rules

- Never delete the repo or its files unless the user explicitly asks to remove the registered configuration.
- Never change unrelated repo settings without asking.
- Tell the user exactly what was saved and what was validated.
- If the user says "new vault", "connect my repo", or "change my folder settings", treat it as a repo-config task and use this skill.
- Keep the workflow conversational and one-step-at-a-time.
