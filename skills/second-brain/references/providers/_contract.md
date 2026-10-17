# Task Provider Contract

Every adapter in this folder (`<name>.md`) implements these operations. The skill only
uses these operations and the normalized fields; provider details stay in the adapter.

## Normalized task

| Field | Type | Notes |
|---|---|---|
| `id` | string | provider's id |
| `project_id` | string | |
| `project_name` | string | |
| `title` | string | |
| `due` | date or null | ISO `YYYY-MM-DD`; null if none |
| `priority` | 0-5 | map provider scale to this; 0 = none |
| `status` | `open` or `done` | |
| `url` | string or null | link to the task in the provider UI |

## Operations

| Operation | Returns |
|---|---|
| `list_projects()` | `[{id, name, archived}]` |
| `list_open_tasks(project_id)` | normalized tasks, all pages |
| `list_completed_since(date)` | normalized tasks completed on/after date |
| `create_task(project_id, title, due?, priority?)` | normalized task |
| `complete_task(id)` | normalized task |

## Rules for every adapter

- Read config only from env vars; never print or log secrets.
- Paginate until a page returns fewer items than requested.
- Idempotent reads; writes only when the caller asks.
- On failure return an error string without credentials; the skill leaves
  `projects.md` unchanged.
- Document env vars, auth, endpoints and quirks in the adapter file.

## Adding a new provider

1. Copy `vikunja.md` to `<name>.md`, rewrite the mapping sections.
2. Set `TASK_PROVIDER=<name>` and its env vars.
3. Run a sync once and check `projects.md`.
