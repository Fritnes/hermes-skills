# Hermes Skills

This repository contains a set of Hermes Agent skills for simple utility work and Obsidian vault automation.

## Repository structure

```text
skills/
├── hello-world/
├── text-summarizer/
├── skill-template/
├── obsidian-templates/
├── obsidian-index/
├── obsidian-lint/
├── obsidian-sync/
└── ...
```

Each folder in `skills/` contains its own `SKILL.md` and any supporting scripts needed for that skill.

## Installed skills

| Skill folder | Purpose | Typical prompt |
|---|---|---|
| `hello-world` | Verifies the skill system is active | "Test hello skill" |
| `text-summarizer` | Summarizes paste text into a short structured answer | "Summarize this article" |
| `skill-template` | Starter template for creating a new skill | "Create a new skill" |
| `obsidian-templates` | Create notes from templates into the right repo/folder | "Create a meeting note" |
| `obsidian-index` | Build and query a searchable vault index | "Find notes about project alpha" |
| `obsidian-lint` | Check for broken links, orphans, duplicates, and missing frontmatter | "Audit my vault" |
| `obsidian-sync` | Safely check status, pull, commit, and push vault repos | "Sync my vault" |

## Install

Copy the folders you want into your Hermes skill directory.

```bash
cp -r skills/hello-world ~/.hermes/skills/
cp -r skills/text-summarizer ~/.hermes/skills/
cp -r skills/obsidian-* ~/.hermes/skills/
```

If you want just a subset, replace the wildcard with specific folders.

## Obsidian vault skills

The Obsidian-related skills are intentionally named with the `obsidian-*` prefix so they stay consistent with the repo convention.

```bash
cp -r skills/obsidian-templates skills/obsidian-index skills/obsidian-lint skills/obsidian-sync ~/.hermes/skills/
```

These skills share a common vault configuration model and can register repo metadata through chat-driven setup.

## Configuration files

The Obsidian skills share configuration under the Hermes vault directory:

```text
~/.hermes/vault/repos.toml
~/.hermes/vault/conventions.md
~/.hermes/vault/index.json
<repo>/.vault.toml
```

## Adding a new skill

1. Create a new folder under `skills/`.
2. Add a `SKILL.md` file with `name` and `description` frontmatter.
3. Keep the folder name aligned with the skill name.
4. Add any supporting scripts or template files needed.
5. Document it in this README.

## License

MIT
