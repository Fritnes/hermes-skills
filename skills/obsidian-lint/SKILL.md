---
name: obsidian-lint
description: Health-check Obsidian vaults registered with git-repo-sync for broken wikilinks, orphan notes, missing frontmatter, duplicate titles, and empty notes. Use when I ask to audit or check my notes.
version: 2.0.0
---

# Obsidian Lint

Read-only audit across all repos.

## Repo selection and first use

Repository names and local paths come from `~/.hermes/git-repos.toml`, managed by `git-repo-sync`. Default lint operations include repos marked `obsidian = true` or containing `.obsidian/` or `.vault.toml`. If the requested repo is not registered or cloned, use `git-repo-sync` to set it up; do not create another repo registry.

Use `--repo <name>` to target one registered repo. Lint conventions live in that repo's `.vault.toml`; inspect the vault and ask before saving changes with `vault_config.py init-repo`.

## Settings to ask about (section `lint` in `<repo>/.vault.toml`)
- **Required frontmatter keys** (default `tags`). Use the "Common frontmatter keys" from `detect` to suggest -> `init-repo --name X --required-keys "title,type,tags"`
- **Folders where orphan notes are fine** (default `daily, templates, inbox`) -> `--orphan-ignore "daily,templates,inbox"`

## Script
`python ~/.hermes/skills/obsidian-lint/scripts/lint.py [--repo X] [--check broken,orphans,frontmatter,duplicates,empty] [--limit N]`

## Workflow
1. Run the lint (all checks, or only what I asked for).
2. Summarize: counts per check, then the 5 most important findings.
3. Propose fixes grouped by type. Wait for my approval before changing ANY file.
4. Apply approved fixes one repo at a time; use git-repo-sync for any requested commit or sync.

## Rules
- The script never modifies files; you must not either without approval.
- Never delete notes. For orphans/duplicates suggest linking or merging; I decide.
