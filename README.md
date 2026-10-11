# Hermes Skills

This repository contains Hermes Agent skills for utility work, Git repository management, and Obsidian vault automation.

## Repository structure

```text
skills/
├── hello-world/
├── text-summarizer/
├── skill-template/
├── git-repo-sync/
├── obsidian-templates/
├── obsidian-index/
├── obsidian-lint/
├── reactive-resume-selfhosted/
├── vikunja/
└── ...
```

Each folder in `skills/` contains its own `SKILL.md` and any supporting scripts needed for that skill.

## Installed skills

| Skill folder | Purpose | Typical prompt |
|---|---|---|
| `hello-world` | Verifies the skill system is active | "Test hello skill" |
| `text-summarizer` | Summarizes paste text into a short structured answer | "Summarize this article" |
| `skill-template` | Starter template for creating a new skill | "Create a new skill" |
| `git-repo-sync` | Register multiple repos and check whether local branches need updating | "Check my home-lab repo" |
| `obsidian-templates` | Create notes or standardize existing notes to one structure | "Create a meeting note" / "Format my notes" |
| `obsidian-index` | Build and query a searchable vault index | "Find notes about project alpha" |
| `obsidian-lint` | Check for broken links, orphans, duplicates, and missing frontmatter | "Audit my vault" |
| `reactive-resume-selfhosted` | Read, edit, and export resumes from a self-hosted Reactive Resume instance | "Review my resume on the homelab server" |
| `vikunja` | Manage tasks in a self-hosted Vikunja instance | "List my open tasks" |

## Install

Copy the folders you want into your Hermes skill directory.

```bash
cp -r skills/hello-world ~/.hermes/skills/
cp -r skills/text-summarizer ~/.hermes/skills/
cp -r skills/git-repo-sync ~/.hermes/skills/
cp -r skills/obsidian-* ~/.hermes/skills/
cp -r skills/reactive-resume-selfhosted ~/.hermes/skills/
cp -r skills/vikunja ~/.hermes/skills/
```

If you want just a subset, replace the wildcard with specific folders.

## Using a skill

Ask Hermes normally and it may select a relevant skill automatically. To explicitly request one, start your message with `/skill-name`, followed by the task. For example:

```text
/git-repo-sync check my home-lab repository
/obsidian-templates create a meeting note about the deployment
/obsidian-templates format all notes in my homelab folder
/reactive-resume-selfhosted review my resume on the homelab server
/vikunja list my open tasks
```

A skill is a package of task-specific instructions and supporting tools for Hermes. It guides how Hermes handles that task; it is not a separate AI, model, or mode of thinking.

## Obsidian vault skills

The Obsidian-related skills are intentionally named with the `obsidian-*` prefix so they stay consistent with the repo convention. Repository names and local paths come from `git-repo-sync`; vault-specific settings stay in each repo's `.vault.toml`.

```bash
cp -r skills/obsidian-templates skills/obsidian-index skills/obsidian-lint ~/.hermes/skills/
```

These skills use the shared Git repository registry and keep only Obsidian-specific conventions in `.vault.toml`.

## Configuration files

Git repo locations are managed by `git-repo-sync`; Obsidian-specific settings and caches are stored here:

```text
~/.hermes/git-repos.toml
~/.hermes/vault/conventions.md
~/.hermes/vault/index.json
<repo>/.vault.toml
```

## Docker Compose setup

Use this repo as a mounted Hermes skill source inside a Docker-based setup.

### Initial setup

```bash
git clone https://github.com/Fritnes/hermes-skills.git
cd hermes-skills
```

Add the repository to your Docker Compose configuration, for example:

```yaml
services:
  hermes:
    image: your-hermes-image
    volumes:
      - ./hermes-skills/skills:/skills:ro
      - ./hermes-data:/data
```

Then add the remote skill source to your Hermes config so Hermes can load the skills from the mounted folder.

Example config idea:

```yaml
skills:
  external_dirs:
    - /skills
```

This keeps the mounted directory as an external skill source without copying the repo into `~/.hermes/skills/`.

### Update later

```bash
cd hermes-skills
git pull
```

Then restart the Hermes container or reload the app so it picks up the latest skills.

## Adding a new skill

1. Create a new folder under `skills/`.
2. Add a `SKILL.md` file with `name` and `description` frontmatter.
3. Keep the folder name aligned with the skill name.
4. Add any supporting scripts or template files needed.
5. Document it in this README.

## License

MIT
