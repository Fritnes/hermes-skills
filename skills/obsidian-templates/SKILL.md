---
name: obsidian-templates
description: Create new Obsidian notes (daily, meeting, project, idea, inbox) from my templates with correct frontmatter, filename and folder, in a repo registered with git-repo-sync. Use when I ask to create, add, or start a note.
version: 2.0.0
---

# Obsidian Templates

## Repo selection and first use

Repository names and local paths come from `~/.hermes/git-repos.toml`, managed by `git-repo-sync`. If the requested repo is not registered or cloned yet, use `git-repo-sync` to set it up; do not create a second Obsidian repo registry or clone it here.

Use `--repo <name>` to target a registered repo. For Obsidian-specific settings, run `vault_config.py detect --path <local_path>`, show the findings, and ask before saving conventions to that repo's `.vault.toml` with `vault_config.py init-repo`. The shared Git registry remains the source of repo paths and remotes.

## Settings to ask about
Run `vault_config.py detect` first; it shows my Obsidian templates folder, daily-notes folder and common frontmatter keys/tags. Then confirm:
- **Templates folder** in the repo (use what `detect` found) -> `init-repo --name X --templates-dir "Templates"`
- **Note types -> folder** (daily, meeting, project, idea, inbox; add my own types) -> `--folder meeting=Meetings --folder daily=Journal`
- **Filename pattern per type** (`{{date}}` = YYYY-MM-DD, `{{title}}`) -> `--naming meeting="{{date}} {{title}}"`
- **Conventions** (required frontmatter keys, tag style, linking habits, language). Draft them from `detect` output, show me, then save:
  `vault_config.py conventions set <<'EOF' ... EOF`
  Before creating any note, read them with `vault_config.py conventions show` and follow them.
My own templates in the repo's templates folder always win over the bundled fallback ones in this skill's `templates/`.

## Script
`python ~/.hermes/skills/obsidian-templates/scripts/new_note.py`
- `--repo X --list` show note types, target folders and which template file is used
- `--repo X --type meeting --title "Q3 planning" --tags work,q3 [--date YYYY-MM-DD] [--dry-run]`

Placeholders: `{{title}} {{date}} {{time}} {{date:FMT}} {{tags}} {{repo}}`.

## Workflow
1. Decide the repo. If not obvious from my request, ask (one short question).
2. Use `--dry-run` for anything non-trivial and show me the target path.
3. Create the note. Then find 2-5 related notes (obsidian-index skill if installed) and add them as `[[links]]` under `## Related` in the new file only.
4. Tell me the path. Do not commit automatically; use git-repo-sync only if I ask to commit or sync.

## Rules
- NEVER overwrite an existing note. If refused, offer to append or pick another title.
- Use only frontmatter keys from the template and my conventions; do not invent keys.
- Never leave unresolved `{{...}}` placeholders in the result.
