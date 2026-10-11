---
name: obsidian-templates
description: Create new Obsidian notes (daily, meeting, project, idea, inbox) from my templates with correct frontmatter, filename and folder, in the right repo. Use when I ask to create/add/start a note. Also handles first-time registration of my vault repos and my note conventions through chat.
version: 2.0.0
---

# Obsidian Templates

## First-time setup (done in chat, before the task)
Config is created by talking to me. Never ask me to edit files by hand, and never edit `repos.toml` / `.vault.toml` yourself; use `vault_config.py`.

1. Run: `python ~/.hermes/skills/obsidian-templates/scripts/vault_config.py status`
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
4. Tell me the path. Do not commit; suggest obsidian-sync.

## Rules
- NEVER overwrite an existing note. If refused, offer to append or pick another title.
- Use only frontmatter keys from the template and my conventions; do not invent keys.
- Never leave unresolved `{{...}}` placeholders in the result.
