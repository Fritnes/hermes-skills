---
title: Taxonomy
type: concept
---

# Taxonomy

Single source of truth for `domain` values and tags. To add a domain, add a row.
Rules: ids are lowercase kebab-case; one nesting level with `/` (parent must exist);
never rename an id (set `status: deprecated` and `replaced_by`).

`task_projects`: provider project names or ids that belong to this domain
(used by task sync to assign `domain`).

## Domains

| id | label | description | task_projects | status |
|---|---|---|---|---|
| work | Work (general) | Cross-company work topics | | active |
| work/company-a | Company A | | | active |
| work/company-b | Company B | | | active |
| work/company-c | Company C | | | active |
| work/company-d | Company D | | | active |
| homelab | Homelab | Infrastructure, services, builds | | active |
| ai | AI | AI tools, models, agents | | active |
| personal | Personal | Life, goals, habits, learning | | active |

## Tags

Free-form tags are discouraged; add vocabulary here first.

| tag | meaning |
|---|---|
| incident | Something broke; postmortem material |
| procedure | Repeatable how-to |
| decision | A recorded choice and its reasons |
