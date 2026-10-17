---
name: second-brain
description: Ingest, compile, sync and query the personal knowledge base at the path in env `SECOND_BRAIN_PATH` (work, projects, homelab, AI, personal life). Use whenever the user sends a URL, document or paste to file away; mentions inbox, weekly review, daily run, projects.md, identity.md, router.md, taxonomy or "second brain"; asks to sync tasks from the task manager into projects.md; asks a question that may be answered from earlier notes, decisions, incidents or procedures; or when a cron job invokes it with a [CRON:daily] or [CRON:weekly] tag. Not for quiz/education content (that belongs in a separate education vault).
version: 1.2.0
author: Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [knowledge-base, wiki, second-brain, projects, inbox]
    related_skills: [llm-wiki, obsidian, vikunja]
---

# Second Brain

Personal knowledge base for work, projects and life. Ingests sources, compiles linked
wiki pages, syncs tasks from the task manager, and answers questions from compiled
knowledge. See `README.md` for setup and the recommended cron jobs.

- **Location:** env `SECOND_BRAIN_PATH` (required)
- **Out of scope:** quiz/education content, secrets (tokens, passwords, keys).

Before any file operation, verify `SECOND_BRAIN_PATH` is set and points to an existing
directory. If it is unset or missing, do not guess or create a vault: ask the user to
configure the path in interactive mode; in cron mode, report the blocker and stop.

## Operating Modes

| Mode | How detected | Rules |
|---|---|---|
| **Interactive** | User is chatting | May ask questions, confirm scope, discuss takeaways |
| **Cron** | Prompt starts with `[CRON:<job>]` | **Never ask questions or wait.** Do the safe part, log it, reply briefly. Anything needing approval goes to `inbox.md` under `## Needs approval` |

## Always Orient First (once per run)

1. Read `SCHEMA.md` (rules, thresholds) and `taxonomy.md` (valid domains).
2. Read `index.md` and the last ~30 lines of `log.md`.
3. Only then act. In a composite cron run (daily), orient once, not per step.

## Architecture

```
$SECOND_BRAIN_PATH/
├── identity.md      who the user is, goals, communication style
├── projects.md      live project state + synced tasks (managed blocks)
├── router.md        lookup table: where everything lives
├── inbox.md         scratchpad; `## Needs approval` section for cron leftovers
├── SCHEMA.md        rules, thresholds, conventions
├── taxonomy.md      the ONLY list of valid domains (and tag vocabulary)
├── index.md         page catalog, grouped by domain
├── log.md           append-only action log
├── weekly/          YYYY-Www.md (ISO week, e.g. 2026-W42)
├── templates/       entity, concept, comparison, query, weekly
├── raw/             immutable sources: articles/ papers/ transcripts/ assets/
├── entities/  concepts/  comparisons/  queries/
```

Skill bundle: `SKILL.md`, `README.md`, `references/providers/*.md` (task manager
adapters), `assets/taxonomy.md` (starter taxonomy to copy into the vault).

## Domains (unified `domain` field)

One field replaces the old `sub_domain` + `org`.

- Value is an id from `taxonomy.md`: a top level (`homelab`, `ai`, `personal`, `work`)
  or one nested level (`work/company-a`, `work/company-b`). Max 2 levels.
- Exactly one primary `domain` per page. Extra context goes in `tags`.
- Prefix match works for queries and indexes: `work` includes all `work/*`.
- **Adding a domain = adding one row to `taxonomy.md`.** Never edit this skill for that.
- **Never invent a domain silently.** Unknown value needed: interactive → propose the new
  row and ask; cron → use the closest parent, add a line to `## Needs approval`.
- Never rename an id. Mark the old row `status: deprecated` with `replaced_by`, then
  migrate pages.
- Legacy `sub_domain`/`org` frontmatter: auto-migrate during lint
  (`sub_domain: work` + `org: company-a` → `domain: work/company-a`).

## Unified Conventions

**Frontmatter (all wiki pages):**
```yaml
---
title: Human readable title
type: entity | concept | comparison | query | weekly
domain: work/company-a            # id from taxonomy.md
tags: [from taxonomy.md vocabulary]
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources: [raw/articles/slug.md]
status: draft | stable | stale
---
```

**Raw files:** `source_url`, `ingested`, `sha256`, `title`. Body is never edited.

**Naming:** lowercase kebab-case ASCII filenames. Content in the source's or user's
language; wikilinks and tags in English.

**Dates:** ISO `YYYY-MM-DD`; weeks via `date +%G-W%V`; timezone from env `TZ`.

**Links:** at least 2 `[[wikilinks]]` per page; no orphans.

**Log line:** `## [YYYY-MM-DD HH:MM] <op> | <title>` + bullets of files touched.
Ops: `ingest`, `tasks`, `weekly`, `inbox`, `query`, `lint`.

**Safety:**
- Never write tokens or credentials to any file or log. Use `[REDACTED]`.
- No pages for passing mentions; thresholds in `SCHEMA.md` (default: central to the
  source, or 2+ mentions).
- Interactive: confirm before touching 10+ pages. Cron: cap at 10 pages per run, defer
  the rest to `## Needs approval`.

## Task Manager (provider-agnostic)

The skill never hardcodes a task manager. It talks to a **provider** through a fixed
contract.

- Active provider: env `TASK_PROVIDER` (default `vikunja`).
- Contract: `references/providers/_contract.md` (operations and normalized fields).
- Adapter: `references/providers/<TASK_PROVIDER>.md` (endpoints, auth, quirks).
- In this skill, use only normalized fields: `id, project_id, project_name, title,
  due, priority, status, url`.
- Task refs in notes: `[<provider>:<id>]`, e.g. `[vikunja:345]`.
- Managed blocks in `projects.md` are provider-neutral:
  ```
  <!-- tasks:start provider=vikunja project=12 domain=work/company-a -->
  - [ ] Task title ([vikunja:345], due 2026-10-20, p3)
  <!-- tasks:end provider=vikunja project=12 -->
  ```
- **Switching provider:** set `TASK_PROVIDER`, add the adapter file, run sync once. Old
  provider blocks are kept and marked `(legacy provider, not synced)`; new blocks are
  created. Nothing is deleted.

## Operations

### 1. Ingest Source

Trigger: URL, document or paste.

1. **Dedupe:** search `raw/` for the same `source_url` or `sha256`. Unchanged → "already
   ingested", stop. Changed → save `slug-YYYYMMDD.md` and note the drift.
2. **Capture:** URL → `web_extract` → `raw/articles/<slug>.md`; paste →
   `raw/transcripts/<slug>.md`; PDF → `raw/papers/`. Add raw frontmatter.
3. **Discuss takeaways** (interactive only).
4. **Compile:** update existing pages before creating new ones. Use `templates/`.
   Set `domain`.
5. **Navigate:** update `index.md` (and `router.md` if a new location type appears),
   append to `log.md`.
6. **Report** every file created or updated.

### 2. Sync Tasks

Trigger: conversation mention, or step of `[CRON:daily]`.

1. Load the provider adapter. Call `list_projects`, then `list_open_tasks` per project
   (adapter handles pagination).
2. Update `projects.md` **only inside managed blocks**. Text outside blocks (user notes,
   status, decisions) is never touched. New project → new heading + block. Project gone
   at provider → keep it, add `(archived YYYY-MM-DD)`.
3. Set each block's `domain` using `task_projects` in `taxonomy.md`; if unmapped, use the
   closest guess in interactive mode (and ask), or `personal` + `## Needs approval` in cron.
4. Update the `Last sync:` / `Provider:` header lines; log counts only (projects, open,
   added, closed).
5. Idempotent: two runs in a row produce no diff except the timestamp.
6. Provider error: log the error without secrets; leave `projects.md` unchanged.

### 3. Weekly Review

Trigger: `[CRON:weekly]` or user request. Two phases, because cron cannot wait.

**Phase A (autonomous):**
1. Create `weekly/<YYYY-Www>.md` from the template with `status: draft`.
2. Pre-fill from the last 7 days: `log.md` entries, tasks completed (provider
   `list_completed_since`), new pages, open inbox items.
3. Run Lint (operation 6); add a short "Brain health" section.
4. Send the 4 questions: What did you ship? What did you learn? What decisions did you
   make? What's next week's focus?

**Phase B (interactive, when the user replies):** find the latest `weekly/*.md` with
`status: draft`, merge the answers, set `status: stable`, promote durable decisions to
concept/entity pages, log it. If the previous week is still `draft`, remind once.

### 4. Query the Brain

1. Read `index.md` / `router.md` for candidates.
2. `search_files` across `.md` (terms in all of the user's languages).
3. Synthesize; cite "Based on [[page-a]] and [[page-b]]…". If the brain lacks the answer,
   say so and offer to ingest a source.
4. File in `queries/` only if novel synthesis or costly to re-derive.

### 5. Inbox Processing

1. Read `inbox.md` (ignore `## Needs approval` items).
2. Route each item: source → operation 1; task → `projects.md` and provider via
   `create_task` if it needs tracking; decision/note → concept or entity page;
   handled → drop; ambiguous → `## Needs approval` with a one-line question.
3. Remove processed items; log counts per category.

### 6. Lint

Report; auto-fix only trivial things (missing `updated`, legacy `sub_domain`/`org`):
- missing frontmatter fields, or `domain` not in `taxonomy.md`
- orphans, broken `[[wikilinks]]`, pages missing from `index.md`
- `draft` older than 14 days; `stable` not updated in 180 days
- raw files whose `sha256` no longer matches
- secret patterns (`token`, `password`, `Bearer`) in any file

## Cron Jobs (two, see README.md)

| Tag | Schedule | Runs |
|---|---|---|
| `[CRON:daily]` | `0 8 * * *` | orient once → operation 5 (if inbox non-empty) → operation 2 |
| `[CRON:weekly]` | `0 18 * * 0` | orient once → operation 3 Phase A (includes lint) |

Cron reply: max 6 lines: what changed (counts), `## Needs approval` items, errors.
Nothing changed and no errors → one line.

## Pitfalls

- Don't ingest quiz/education content.
- Don't overwrite `projects.md`; edit only managed blocks.
- Don't hardcode a task manager name in logic; use the provider contract.
- Don't ask questions in cron mode.
- Don't invent domains or rename domain ids.
- Don't store secrets; don't edit raw files after capture.
- Log everything; `log.md` is the audit trail.
