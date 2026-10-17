# Provider: Vikunja

Env:
- `TASK_PROVIDER=vikunja`
- `VIKUNJA_URL` (required; API base, e.g. `https://vikunja.example.com/api/v1`)
- `VIKUNJA_TOKEN` (API token; send as `Authorization: Bearer $VIKUNJA_TOKEN`; never log)

## Quirks

- Creation (tasks, labels, comments) uses `PUT`; updates use `POST`.
- The comments field key is `comment`.
- List endpoints are paginated with `page` and `per_page`.
- A `due_date` of `0001-01-01T00:00:00Z` means "no due date" → normalized `due: null`.
- Confirm exact paths and filter syntax for your version at your instance's Swagger
  docs (`/api/v1/docs`) before first use.

## Mapping

| Contract operation | Vikunja |
|---|---|
| `list_projects` | `GET /projects` |
| `list_open_tasks` | tasks of a project filtered with `done = false` |
| `list_completed_since` | tasks filtered with `done = true && done_at >= <date>` |
| `create_task` | `PUT /projects/{id}/tasks` |
| `complete_task` | `POST /tasks/{id}` with `done: true` |

| Normalized | Vikunja field |
|---|---|
| `id` | `id` |
| `project_id` | `project_id` |
| `title` | `title` |
| `due` | `due_date` (date part) |
| `priority` | `priority` (0-5, same scale) |
| `status` | `done` → `done`/`open` |
| `url` | `<web base>/tasks/<id>` |
