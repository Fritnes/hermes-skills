# Vikunja API quick reference

Base: `$VIKUNJA_URL/api/v1` - header `Authorization: Bearer $VIKUNJA_TOKEN`.
Full, version-accurate docs are served by the instance itself at `$VIKUNJA_URL/api/v1/docs`.

## Verbs convention
`PUT` = create, `POST` = update, `GET` = read, `DELETE` = remove.

## Endpoints used by the CLI

| Action | Request | Body |
|---|---|---|
| List projects | `GET /projects` | - |
| List project tasks | `GET /projects/{id}/tasks?filter=done = false&page=N&per_page=50` | - |
| Get task | `GET /tasks/{id}` | - |
| Create task | `PUT /projects/{id}/tasks` | `{"title": "..."}` |
| Update task | `POST /tasks/{id}` | full task object |
| Add comment | `PUT /tasks/{id}/comments` | `{"comment": "..."}` |
| List labels | `GET /labels` | - |
| Add label to task | `PUT /tasks/{id}/labels` | `{"label_id": 3}` |

## Useful extras (not in the CLI yet)

Send these as fields on `POST /tasks/{id}` (fetch the task first, modify, post back whole):

- `due_date`: ISO 8601, e.g. `"2026-10-20T12:00:00+03:00"`
- `priority`: integer 0-5
- `description`: HTML string
- `project_id`: moves the task to another project
- `percent_done`: float 0-1

Other endpoints: `PUT /tasks/{id}/assignees` (`{"user_id": N}`), `DELETE /tasks/{id}/labels/{label_id}`,
`PUT /labels` (`{"title": "...", "hex_color": "ff0000"}`), `DELETE /tasks/{id}`.

## Status codes
`200/201` success, `401` bad or expired token, `403` token lacks permission for that resource, `404` wrong ID, `412` invalid body.
