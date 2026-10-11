#!/usr/bin/env python3
"""
Vikunja CLI - direct REST API tool. No LLM required.

Configuration (environment variables):
    VIKUNJA_IP               Server IP or hostname, e.g. 192.168.8.1     (required*)
    VIKUNJA_PORT             Server port                                 (default 3456)
    VIKUNJA_API_KEY          API token with task/project/label access    (required)
    VIKUNJA_DEFAULT_PROJECT  Project ID used when `create default ...`   (optional)

    * Alternatively set VIKUNJA_URL (full base URL, overrides IP/PORT) and/or
      VIKUNJA_TOKEN (alias for VIKUNJA_API_KEY).

Usage:
    vikunja_cli.py list [project_id]
    vikunja_cli.py show <task_id>
    vikunja_cli.py projects
    vikunja_cli.py labels
    vikunja_cli.py create <project_id|default> <title>
    vikunja_cli.py done <task_id>
    vikunja_cli.py comment <task_id> <text>
    vikunja_cli.py label <task_id> <label_id>
"""

import os
import sys

import requests

TIMEOUT = 15
PAGE_SIZE = 50


def _config():
    url = os.environ.get("VIKUNJA_URL", "").rstrip("/")
    if not url:
        ip = os.environ.get("VIKUNJA_IP", "")
        port = os.environ.get("VIKUNJA_PORT", "3456")
        if ip:
            url = f"http://{ip}:{port}"
    token = os.environ.get("VIKUNJA_API_KEY") or os.environ.get("VIKUNJA_TOKEN", "")
    if not url or not token:
        sys.exit(
            "❌ Set VIKUNJA_IP (and optionally VIKUNJA_PORT) plus VIKUNJA_API_KEY first.\n"
            "   e.g. export VIKUNJA_IP=192.168.8.1 VIKUNJA_PORT=3456 VIKUNJA_API_KEY=<token>"
        )
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    return url, headers


BASE_URL, HEADERS = _config()


def api(method, path, **kwargs):
    """Call the API; exit with a readable error on connection failure."""
    try:
        return requests.request(
            method, f"{BASE_URL}/api/v1{path}", headers=HEADERS, timeout=TIMEOUT, **kwargs
        )
    except requests.RequestException as e:
        sys.exit(f"❌ Cannot reach Vikunja at {BASE_URL}: {e}")


def get_all(path, params=None):
    """Fetch every page of a list endpoint (Vikunja paginates, default 50/page)."""
    items, page = [], 1
    while True:
        p = dict(params or {}, page=page, per_page=PAGE_SIZE)
        r = api("GET", path, params=p)
        if r.status_code != 200:
            sys.exit(f"❌ Error: {r.status_code} - {r.text}")
        batch = r.json() or []
        items.extend(batch)
        if len(batch) < PAGE_SIZE:
            return items
        page += 1


def fail(r):
    print(f"❌ Error: {r.status_code} - {r.text}")
    sys.exit(1)


def list_projects():
    projects = [p for p in get_all("/projects") if p.get("id", 0) > 0]
    for p in projects:
        print(f"#{p['id']}  {p['title']}")


def list_labels():
    labels = get_all("/labels")
    if not labels:
        print("No labels defined.")
    for l in labels:
        print(f"#{l['id']}  {l['title']}")


def list_tasks(project_id=None):
    """List open tasks grouped by project (or for one project)."""
    projects = get_all("/projects")
    if project_id:
        projects = [p for p in projects if str(p.get("id")) == str(project_id)]

    output, total_open = [], 0
    for p in projects:
        pid = p.get("id", 0)
        if pid < 0:  # saved filters / favorites are virtual projects
            continue
        tasks = get_all(f"/projects/{pid}/tasks", {"filter": "done = false"})
        tasks = [t for t in tasks if not t.get("done")]
        if tasks:
            output.append(f"**{p['title']} tasks:**")
            output += [f"   • `#{t['id']}` {t['title']}" for t in tasks]
            output.append("")
            total_open += len(tasks)

    if not output:
        print("✅ No open tasks found!")
    else:
        print(f"📋 **Total Open Tasks: {total_open}**\n")
        print("\n".join(output))


def show_task(task_id):
    r = api("GET", f"/tasks/{task_id}")
    if r.status_code != 200:
        fail(r)
    t = r.json()
    labels = ", ".join(l["title"] for l in (t.get("labels") or [])) or "-"
    print(f"#{t['id']} {t['title']}")
    print(f"  project: {t.get('project_id')}  done: {t.get('done')}  labels: {labels}")
    if t.get("description"):
        print(f"  description: {t['description']}")


def mark_done(task_id):
    """Mark done. Fetch-modify-post so POST doesn't blank unspecified fields."""
    r = api("GET", f"/tasks/{task_id}")
    if r.status_code != 200:
        fail(r)
    task = r.json()
    task["done"] = True
    r = api("POST", f"/tasks/{task_id}", json=task)
    if r.status_code in (200, 201, 204):
        print(f"✅ Task #{task_id} marked as done.")
    else:
        fail(r)


def add_comment(task_id, text):
    r = api("PUT", f"/tasks/{task_id}/comments", json={"comment": text})
    if r.status_code in (200, 201, 204):
        print(f"💬 Comment added to task #{task_id}.")
    else:
        fail(r)


def create_task(project_id, title):
    if project_id in (None, "", "default"):
        project_id = os.environ.get("VIKUNJA_DEFAULT_PROJECT")
        if not project_id:
            sys.exit("❌ No project given and VIKUNJA_DEFAULT_PROJECT is not set.")
    r = api("PUT", f"/projects/{project_id}/tasks", json={"title": title})
    if r.status_code in (200, 201):
        d = r.json()
        print(f"✅ Task created! ID: {d.get('id')}, Title: {d.get('title')}")
    else:
        fail(r)


def add_label(task_id, label_id):
    r = api("PUT", f"/tasks/{task_id}/labels", json={"label_id": int(label_id)})
    if r.status_code in (200, 201, 204):
        print(f"🏷 Label {label_id} added to task #{task_id}.")
    else:
        fail(r)


USAGE = __doc__.split("Usage:")[1].strip()


def need(n, usage):
    if len(sys.argv) < n:
        sys.exit(f"Usage: vikunja_cli.py {usage}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(f"Usage:\n{USAGE}")

    cmd = sys.argv[1].lower()
    if cmd == "list":
        list_tasks(sys.argv[2] if len(sys.argv) > 2 else None)
    elif cmd == "show":
        need(3, "show <task_id>")
        show_task(sys.argv[2])
    elif cmd == "projects":
        list_projects()
    elif cmd == "labels":
        list_labels()
    elif cmd == "done":
        need(3, "done <task_id>")
        mark_done(sys.argv[2])
    elif cmd == "comment":
        need(4, "comment <task_id> <text>")
        add_comment(sys.argv[2], " ".join(sys.argv[3:]))
    elif cmd == "create":
        need(4, "create <project_id|default> <title>")
        create_task(sys.argv[2], " ".join(sys.argv[3:]))
    elif cmd == "label":
        need(4, "label <task_id> <label_id>")
        add_label(sys.argv[2], sys.argv[3])
    else:
        sys.exit(f"Unknown command: {cmd}\nUsage:\n{USAGE}")
