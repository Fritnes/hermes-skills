# Reactive Resume API notes

Base: `<instance>/api/openapi` · Auth header: `x-api-key: <key>` · Docs: https://docs.rxresu.me (index with every page: https://docs.rxresu.me/llms.txt)

## Contents
- Endpoints
- Confirming paths I haven't verified
- Resume `data` layout
- Item templates
- Patch recipes
- Error codes

## Endpoints

Verified from the published docs:

| Purpose | Method + path |
|---|---|
| List resumes (no content) | `GET /resumes` (filters: tags; sort) |
| Get resume with `data` | `GET /resumes/{id}` |
| Patch `data` (JSON Patch) | `PATCH /resumes/{id}` body `{"operations":[…], "expectedUpdatedAt":"…"}` |
| Update name / slug / tags / isPublic, or replace whole `data` | `PUT /resumes/{id}` (only sent fields change) |
| Lock / unlock | `POST /resumes/{id}/lock` body `{"isLocked": true|false}` |
| Export | `GET /resumes/{id}/exports/{pdf|docx|markdown|json}` |
| Set public password | `PUT /resumes/{id}/password` |
| Update stream (metadata only) | `GET /resumes/{id}/updates` |

Also documented by name (confirm exact paths before use, see below): create resume, duplicate resume, import resume, move to Trash, restore from Trash, list/name/restore resume versions, ATS check, tags list, upload file.

## Confirming paths I haven't verified

The docs index lists these endpoints but this reference only guarantees the table above. To get an exact path/body:
- Open the matching page from https://docs.rxresu.me/llms.txt (e.g. "Duplicate a resume") - the OpenAPI block shows the path and body.
- Or fetch the full spec: https://docs.rxresu.me/spec.json.
- Then call it with `rr.py request METHOD PATH --body '…'`. If a 404 comes back, the path is wrong; don't guess repeatedly.

Self-hosted instances can run an older or newer version than the hosted docs; if a field is rejected, trust the validation error over this file.

## Resume `data` layout (JSON Pointer paths for patches)

```
/picture              hidden,url,size,rotation,aspectRatio,borderRadius,borderColor,borderWidth,shadowColor,shadowWidth
/basics               name, headline, email, phone, location, website{url,label}, customFields[{id,icon,text,link}]
/summary              title, icon, columns, hidden, keepTogether, startOnNewPage, content (HTML)
/sections/<key>       title, icon, columns, hidden, keepTogether, startOnNewPage, items[]
    keys: profiles, experience, education, projects, skills, languages,
          interests, awards, certifications, publications, volunteer, references
/customSections[]     same section fields + id (UUID) + type (summary|experience|education|profiles|…) + items[]
/metadata/template    template name (must be an available one)
/metadata/design/colors/primary   "rgba(r, g, b, a)"
/metadata/page/dateFormat         short | long | numeric | iso
```

Item index `-` appends (`/sections/skills/items/-`); `0` inserts first. Custom sections are addressed by array position (`/customSections/0/items/-`), so read the array to find the index.

## Item templates

Use these only as a starting point. **Prefer copying an existing item from the user's own resume** (via `get`) so field names match their instance version exactly. Always: fresh UUID `id`, `"hidden": false`.

`website` objects are `{"url":"","label":""}`; some versions also require `"inlineLink": false`. If validation complains, add/remove it.

Dated item types (experience, education, projects, volunteer; experience `roles[]`) use `dates`; leave `period` as `""` and let the server fill it. Single-date types (awards, certifications, publications) use `dates.start` only and leave `date` as `""`.

```jsonc
// experience
{"id":"<uuid>","hidden":false,"company":"Acme","position":"Engineer","location":"Remote",
 "period":"","dates":{"start":"2022-03","end":null,"present":true},
 "website":{"url":"","label":""},"description":"<ul><li>…</li></ul>","roles":[]}

// education
{"id":"<uuid>","hidden":false,"school":"…","degree":"…","area":"…","grade":"","location":"",
 "period":"","dates":{"start":"2016","end":"2020","present":false},
 "website":{"url":"","label":""},"description":""}

// skills
{"id":"<uuid>","hidden":false,"icon":"","iconColor":"","name":"Python","proficiency":"Advanced","level":4,"keywords":["FastAPI","pandas"]}

// languages
{"id":"<uuid>","hidden":false,"language":"English","fluency":"C1","level":4}

// projects
{"id":"<uuid>","hidden":false,"name":"…","period":"","dates":{"start":"2024","end":null,"present":true},
 "website":{"url":"","label":""},"description":"<p>…</p>"}

// certifications (awards: title+awarder; publications: title+publisher)
{"id":"<uuid>","hidden":false,"title":"…","issuer":"…","date":"","dates":{"start":"2023-05","end":null,"present":false},
 "website":{"url":"","label":""},"description":""}
```

Generate UUIDs with `python3 -c "import uuid;print(uuid.uuid4())"`.

## Patch recipes

Write these into a file and run `rr.py patch <id> --ops file.json --dry-run`, then without `--dry-run`.

```json
[{"op":"replace","path":"/basics/headline","value":"Senior Backend Engineer"}]
```
```json
[{"op":"replace","path":"/summary/content","value":"<p>Backend engineer with …</p>"}]
```
Rewrite one experience entry's bullets (guard with `test` on the company):
```json
[
 {"op":"test","path":"/sections/experience/items/0/company","value":"Acme"},
 {"op":"replace","path":"/sections/experience/items/0/description","value":"<ul><li>…</li><li>…</li></ul>"}
]
```
Change dates:
```json
[{"op":"replace","path":"/sections/experience/items/0/dates","value":{"start":"2021","end":"2024-06","present":false}}]
```
Reorder (first experience entry to third place):
```json
[{"op":"move","from":"/sections/experience/items/0","path":"/sections/experience/items/2"}]
```
Hide an entry or a section (reversible, preferred over delete):
```json
[{"op":"replace","path":"/sections/experience/items/3/hidden","value":true}]
```
```json
[{"op":"replace","path":"/sections/interests/hidden","value":true}]
```
Add a skill at the end: `{"op":"add","path":"/sections/skills/items/-","value":{…skills template…}}`
Remove (confirm with user first): `{"op":"remove","path":"/sections/skills/items/1"}`
Template / color: `/metadata/template` and `/metadata/design/colors/primary`.

Name, slug, tags, public flag are outside `data`:
```bash
python3 scripts/rr.py put <id> --json '{"name":"Backend CV 2026","tags":["backend"]}'
```

If a patch adds a section of type `cover-letter`, the server moves it into a separate cover letter linked to the resume (`/cover-letters` endpoints) and removes the section.

## Error codes

| HTTP | Code | Meaning / action |
|---|---|---|
| 400 | `BAD_REQUEST` | Malformed body (empty `operations`, missing `value`/`from`) |
| 400 | `INVALID_PATCH_OPERATIONS` | Path not found, `test` failed, or result fails schema. `data` has the failing `index`; fix that op |
| 401 | `UNAUTHORIZED` | Key missing, revoked or expired. Ask the user for a new one |
| 403 | `RESUME_LOCKED` | Resume locked. Only unlock with explicit user OK |
| 404 | `NOT_FOUND` | Wrong id, or belongs to another account |
| 409 | `RESUME_VERSION_CONFLICT` | Changed since read. `get` again, rebuild ops, retry |
