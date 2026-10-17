# Second Brain skill

Personal knowledge base operator for Hermes. Ingests sources, compiles wiki pages,
syncs tasks from your task manager into `projects.md`, runs a weekly review.

## Setup

1. Set `SECOND_BRAIN_PATH` to the vault location.
2. Copy `assets/taxonomy.md` to `$SECOND_BRAIN_PATH/taxonomy.md` and edit domains.
3. Ensure `$SECOND_BRAIN_PATH` has `SCHEMA.md`, `index.md`, `log.md`, `inbox.md`,
   `projects.md`, `router.md`, `identity.md`, `raw/`, and these templates:
   `templates/entity.md`, `templates/concept.md`, `templates/comparison.md`,
   `templates/query.md`, and `templates/weekly.md`. These vault files are not scaffolded
   by the skill bundle.
4. Configure the environment:

| Var | Default | Purpose |
|---|---|---|
| `SECOND_BRAIN_PATH` | none (required) | vault location, e.g. `/data/second-brain` |
| `TASK_PROVIDER` | `vikunja` | which adapter in `references/providers/` |
| `VIKUNJA_URL` | none (required for Vikunja) | Vikunja API base URL |
| `VIKUNJA_TOKEN` | none (required for Vikunja) | Vikunja API token (secret) |

Vikunja credentials are needed only when `TASK_PROVIDER=vikunja`; configure the
environment variables required by the selected provider's adapter otherwise.

## Recommended cron jobs: 2 instead of 3

| Job | Schedule | Why |
|---|---|---|
| **second-brain-daily** | `0 8 * * *` | inbox sweep, then task sync, one run, one message |
| **second-brain-weekly** | `0 18 * * 0` | weekly review draft + lint |

Why this is better than 3 jobs:
- **One orientation per run.** Separate sync and sweep jobs each re-read `SCHEMA.md`,
  `index.md` and `log.md`. Merged, that cost is paid once.
- **Correct order.** Inbox first, then sync. A task you dropped in `inbox.md` gets created
  in the task manager and appears in `projects.md` in the same run. With separate jobs
  (sync 08:00, sweep 20:00) it showed up a day late.
- **One notification instead of two.** Less noise at origin.
- **Fresh daily state.** Everything is current at 08:00, before your day starts.

Trade-off: something you write in `inbox.md` in the evening waits until the next morning.
When you want it filed now, say "process inbox" in chat (interactive run).

### Prompts (copy-paste, "Deliver to origin")

**second-brain-daily**
```
[CRON:daily] Use the second-brain skill. Orient once (SCHEMA.md, taxonomy.md, index.md, recent log.md). Step 1: if inbox.md has unprocessed items, run the inbox sweep (route to raw/, projects.md and the task manager, concept/entity pages, or archive; clear processed items). Step 2: sync projects and open tasks from the task manager into projects.md (managed blocks only, preserve my edits, assign domain from taxonomy.md). Log everything in log.md. Do not ask questions; put anything needing my decision under "Needs approval" in inbox.md. Reply in max 6 lines. Deliver to origin.
```

**second-brain-weekly**
```
[CRON:weekly] Use the second-brain skill. Create the review note weekly/<current ISO week>.md with status draft, pre-fill it from log.md and tasks completed this week, run lint and add a "Brain health" section, then send me the 4 questions: What did you ship? What did you learn? What decisions did you make? What's next week's focus? When I reply, fill the note, set it to stable and log it. Deliver to origin.
```

Your reply to the weekly questions is handled as a normal chat message: the skill finds
the latest `draft` weekly note and completes it.

### When to add a third job

Only if you actually need it:
- Inbox is used heavily during the day → add `0 13 * * 1-5` running just the inbox sweep.
- Vault grows past ~500 pages → add a monthly `[CRON:monthly]` full lint on the 1st.

Otherwise keep two.

## Domains

One field `domain` (replaces `sub_domain` + `org`). Examples: `work/company-a`, `homelab`.
Add a new one by adding a row to `taxonomy.md`; no skill edits needed. Existing pages with
`sub_domain`/`org` are migrated automatically by the weekly lint.

## Changing the task manager later

1. Copy `references/providers/vikunja.md` to `references/providers/<new>.md` and fill in the
   mapping (contract in `_contract.md`).
2. Set `TASK_PROVIDER=<new>` and its credentials.
3. Run a daily job manually once. Old blocks in `projects.md` are kept as legacy; new
   blocks are created. Update `task_projects` in `taxonomy.md` for the new project names.

No changes to `SKILL.md` or the cron prompts are required, because the prompts say
"task manager", not "Vikunja".
