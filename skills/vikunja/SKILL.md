---
name: vikunja
description: Manage tasks in a self-hosted Vikunja instance through its REST API. Use when the user asks about Vikunja tasks, projects, labels, or to-dos, including listing, creating, completing, commenting on, or labeling a task.
compatibility: Requires Python 3 with `requests`, network access to the Vikunja server, and VIKUNJA_URL plus VIKUNJA_TOKEN (or VIKUNJA_IP plus VIKUNJA_API_KEY) environment variables.
---

# Vikunja task management

Vikunja is a self-hosted to-do app. This skill drives it through `scripts/vikunja_cli.py`, a thin wrapper over the REST API. Use the script instead of hand-writing `curl` or `requests` calls: it already handles pagination, error output and the Vikunja quirks listed below, and it needs no LLM.

## Setup and instance selection

The CLI uses one Vikunja instance per process. It reads configuration from environment variables; it does not currently support `--instance` or read a named-instance config file.

- Set `VIKUNJA_URL` to the base URL and `VIKUNJA_TOKEN` to the API token. Alternatively, set `VIKUNJA_IP`, optional `VIKUNJA_PORT` (default `3456`), and `VIKUNJA_API_KEY`. `VIKUNJA_URL` takes precedence over the IP/port pair; `VIKUNJA_API_KEY` takes precedence over `VIKUNJA_TOKEN`.
- Optionally set `VIKUNJA_DEFAULT_PROJECT` for `create default ...`.
- If the user has multiple instances, ask which one to use, then run the CLI with that instance's URL and token supplied through the environment. Do not silently use one instance's credentials for another.
- If configuration is missing, ask for the server URL and token. Never guess credentials, put tokens in this skill or other repository files, or repeat a token in chat or command output. Use a trusted local secret/configuration mechanism; before editing Hermes configuration, inspect its actual format and location instead of assuming a schema.
- If the current environment cannot securely supply the token, explain how the user can configure it locally rather than requesting the secret in chat.

## Commands

Run from this skill's directory: `python3 scripts/vikunja_cli.py <command>`

| Command | Purpose |
|---|---|
| `list [project_id]` | Open tasks grouped by project, or for one project |
| `show <task_id>` | Title, project, done state, labels, description |
| `projects` | Project IDs and titles |
| `labels` | Label IDs and titles |
| `create <project_id\|default> <title>` | New task; `default` uses `VIKUNJA_DEFAULT_PROJECT` |
| `done <task_id>` | Mark a task complete |
| `comment <task_id> <text>` | Add a comment (text may be several words, no quoting needed) |
| `label <task_id> <label_id>` | Attach an existing label |

## Workflow guidance

- **Resolve names to IDs first.** Users say "the HomeLabs project" or "the urgent label", but the API needs numeric IDs. Run `projects` or `labels` and match, rather than guessing. If several match, ask which one.
- **Verify task identity before mutation.** If the user refers to a task by description, run `list` or `show` to identify it. Ask which task they mean if more than one matches; after a successful change, state the task ID and title.
- **Create then label.** `create` prints the new task ID; use it for a follow-up `label` or `comment` call when the user wants both.
- **Report results plainly.** The script output is already formatted with the task ID and title; relay it and add only what the user needs (for example the new task's ID).

## Vikunja quirks (why the script behaves as it does)

- Lists are paginated (50 per page by default). The script walks all pages so counts are not silently truncated.
- Projects with a negative ID are virtual (saved filters, favorites). They are skipped when listing so tasks are not double-counted.
- Updating a task is `POST /tasks/{id}`, and omitted fields can be reset to empty. `done` therefore fetches the task, flips `done`, and posts the whole object back.
- Creation and sub-resources use `PUT` (`PUT /projects/{id}/tasks`, `PUT /tasks/{id}/comments`, `PUT /tasks/{id}/labels`); updates use `POST`. This is the reverse of most REST APIs, so do not "correct" it.

For endpoint details if you need something the CLI does not cover (due dates, assignees, priorities, moving tasks), read `references/api.md`.
