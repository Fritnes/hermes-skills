---
name: obsidian-templates
description: Create Obsidian notes from templates or reformat existing notes into one consistent structure in a repo registered with git-repo-sync. Use when I ask to create, add, start, standardize, or reformat notes.
version: 3.0.0
---

# Obsidian Notes and Templates

Use one shared note structure for both newly created and reformatted notes:

```markdown
---
title: "Descriptive Title"
category: "Directory Name"
tags:
  - tag-one
  - tag-two
---

## Description
Brief description of the note's subject and purpose.

## Main Block
The note's useful content, organized for readability.
```

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

## Create a note

1. Decide the repo. If not obvious from my request, ask (one short question).
2. Use `--dry-run` for anything non-trivial and show me the target path.
3. Create the note. Then find 2-5 related notes (obsidian-index skill if installed) and add them as `[[links]]` under `## Related` in the new file only.
4. Keep the shared structure above. Put type-specific content or extra sections inside `## Main Block`; if a user template conflicts with the shared structure, explain the difference and ask before changing the template.
5. Tell me the path. Do not commit automatically; use git-repo-sync only if I ask to commit or sync.

## Reformat existing notes

1. Resolve the target vault from the shared Git repo registry. If no repo or directory is clear, ask which one. If the repo is not registered or cloned, use `git-repo-sync` first.
2. Respect `.vault.toml` ignore rules. Skip `.git/`, `.obsidian/`, `.trash/`, attachments, dependency folders, and template files unless explicitly included. Only process Markdown notes; do not rename, move, or delete them.
3. Check Git status, count eligible notes, and inspect 3-5 representative notes across the target. Report existing changes that overlap the target.
4. Propose the scope and exact formatting rules, show a before/after example from a real note, and get approval before any bulk write.
5. Preserve the full useful body, including code blocks, links, embeds, callouts, and meaningful headings, under `## Main Block`. Do not replace notes with keyword summaries.
6. Set `title` from existing meaningful metadata or the filename in Title Case; set `category` to the immediate parent folder, or vault name for root notes. Write tags as lowercase YAML list items, retaining useful existing tags and adding only clearly relevant ones.
7. Write a concise `## Description` based on the actual note. Prefer an existing accurate summary; otherwise summarize the note faithfully.
8. Remove only confirmed artifacts, such as duplicate Summary/Tags sections when their information is represented in Description/frontmatter, tag-only lines, stale generated preview comments, and malformed export lines. Preserve unrelated metadata and ask before removing keys that do not fit the standard template.
9. Skip malformed YAML, ambiguous content, or conflicting metadata rather than guessing. Validate each changed note has frontmatter, title/category/tags, exactly one `## Description` and `## Main Block`, no unresolved placeholders, and retained substantive content. Report changed, skipped, and failed counts.
10. Never commit or push automatically. Use `git-repo-sync` only if I separately ask to review, commit, or sync.

### Tag suggestions

Use topic mappings only when supported by note content: SSH (`ssh`, `security`, `linux`, `remote-access`); Dell hardware (`tech`, `linux`, `hardware`, `dell`); Intune (`intune`, `powershell`, `windows`, `deployment`); Linux administration (`linux`, `system-admin`); Cisco/networking (`cisco`, `networking`); Bash (`bash`, `scripting`, `linux`); Nextcloud (`nextcloud`, `cloud`, `storage`); WHOIS (`whois`, `network`, `domain`, `information`). If no topic is clear, use `tech` and `documentation` only when appropriate.

If a file changes concurrently or a batch write fails, stop, re-read affected files, and report the exact state before continuing.

## Rules
- NEVER overwrite an existing note. If refused, offer to append or pick another title.
- Use only frontmatter keys from the template and my conventions; do not invent keys.
- Never leave unresolved `{{...}}` placeholders in the result.
