#!/usr/bin/env python3
"""rr.py - tiny CLI for a self-hosted Reactive Resume instance.

Standard library only (Python 3.8+). Stores the instance address and API key in
~/.config/reactive-resume/config.json (mode 600). RR_BASE_URL / RR_API_KEY
environment variables override the stored values.

Commands:
  config set [--url URL] [--key KEY] [--insecure]   save connection details
  config show                                       show them (key masked)
  config clear                                      delete stored details
  check                                             verify URL + key work
  list [--tag TAG] [--search TEXT]                  list resumes (no content)
  get ID [--out FILE]                               full resume incl. data
  patch ID --ops FILE|-  [--dry-run] [--no-lock] [--no-backup]
  put ID --json '{"name": "..."}'                   name / slug / tags / isPublic
  lock ID | unlock ID
  export ID --format pdf|docx|markdown|json --out FILE
  backup ID                                         save a JSON snapshot locally
  request METHOD PATH [--body JSON|@file]           raw call under /api/openapi
"""
import argparse
import getpass
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("RR_CONFIG_DIR", Path.home() / ".config" / "reactive-resume"))
CONFIG_FILE = CONFIG_DIR / "config.json"
BACKUP_DIR = CONFIG_DIR / "backups"
API_PREFIX = "/api/openapi"
TIMEOUT = 60


def die(msg, code=1):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def normalize_url(raw):
    """Accept '192.168.1.20:3000', 'http://host:3000/', or '.../api/openapi'."""
    u = (raw or "").strip()
    if not u:
        die("empty URL")
    if "://" not in u:
        u = "http://" + u
    u = u.rstrip("/")
    if u.endswith(API_PREFIX):
        u = u[: -len(API_PREFIX)]
    if not urllib.parse.urlparse(u).netloc:
        die(f"could not parse URL: {raw!r}")
    return u


def read_file_config():
    try:
        return json.loads(CONFIG_FILE.read_text())
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        die(f"{CONFIG_FILE} is not valid JSON; run `config clear` and set it again")


def write_file_config(cfg):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(CONFIG_DIR, 0o700)
    except OSError:
        pass
    fd = os.open(CONFIG_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(cfg, f, indent=2)
    try:
        os.chmod(CONFIG_FILE, 0o600)
    except OSError:
        pass


def get_config():
    cfg = read_file_config()
    url = os.environ.get("RR_BASE_URL") or cfg.get("url")
    key = os.environ.get("RR_API_KEY") or cfg.get("api_key")
    insecure = bool(cfg.get("insecure")) or os.environ.get("RR_INSECURE") == "1"
    if not url or not key:
        die("not configured. Run: rr.py config set --url <ip:port or https://host> --key <api key>")
    return normalize_url(url), key, insecure


def mask(key):
    return key[:4] + "…" + key[-4:] if key and len(key) > 10 else "****"


def request(method, path, body=None, expect_binary=False):
    base, key, insecure = get_config()
    url = base + API_PREFIX + path
    data = None
    headers = {"x-api-key": key, "Accept": "application/json", "User-Agent": "rr-skill/1.0"}
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    ctx = None
    if insecure and url.startswith("https"):
        ctx = ssl._create_unverified_context()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx) as r:
            raw = r.read()
            status = r.status
    except urllib.error.HTTPError as e:
        raw, status = e.read(), e.code
    except urllib.error.URLError as e:
        die(f"cannot reach {base}: {e.reason}")
    except TimeoutError:
        # Mutations are not idempotent: never blindly retry. Re-read first.
        die(f"timed out calling {method} {path}. If this was a write, GET the resume to see "
            "whether it was applied before trying again.")
    if expect_binary and status < 400:
        return status, raw
    try:
        parsed = json.loads(raw) if raw else None
    except json.JSONDecodeError:
        parsed = raw.decode("utf-8", "replace")
    return status, parsed


def ok_or_die(status, payload, what):
    if status >= 400:
        hint = ""
        if status == 401:
            hint = " (API key missing, revoked or expired)"
        elif status == 403:
            hint = " (resume locked, or the key is read-only)"
        elif status == 404:
            hint = " (not found, or not yours)"
        elif status == 409:
            hint = " (resume changed since you read it: re-read and rebuild the patch)"
        die(f"{what} failed: HTTP {status}{hint}\n{json.dumps(payload, indent=2) if not isinstance(payload, str) else payload}")


def out_json(obj):
    print(json.dumps(obj, indent=2, ensure_ascii=False))


def write_private_file(path, content):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(content if isinstance(content, bytes) else content.encode("utf-8"))
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


# ---------------------------------------------------------------- commands
def cmd_config(a):
    if a.action == "set":
        cfg = read_file_config()
        url = a.url or input("Reactive Resume address (e.g. 192.168.1.20:3000 or https://cv.example.com): ")
        key = a.key or getpass.getpass("API key (input hidden): ")
        cfg["url"] = normalize_url(url)
        cfg["api_key"] = key.strip()
        cfg["insecure"] = a.insecure
        write_file_config(cfg)
        print(f"saved to {CONFIG_FILE} (mode 600): {cfg['url']}  key {mask(cfg['api_key'])}")
    elif a.action == "show":
        cfg = read_file_config()
        env_url, env_key = os.environ.get("RR_BASE_URL"), os.environ.get("RR_API_KEY")
        print(json.dumps({
            "config_file": str(CONFIG_FILE),
            "url": normalize_url(env_url) if env_url else cfg.get("url"),
            "api_key": mask(env_key or cfg.get("api_key", "")),
            "insecure_tls": bool(cfg.get("insecure")),
            "source": "environment" if env_url or env_key else "config file",
        }, indent=2))
    elif a.action == "clear":
        try:
            CONFIG_FILE.unlink()
            print("removed", CONFIG_FILE)
        except FileNotFoundError:
            print("nothing to remove")


def cmd_check(a):
    status, payload = request("GET", "/resumes")
    ok_or_die(status, payload, "check")
    n = len(payload) if isinstance(payload, list) else "?"
    print(f"OK - connected, key accepted, {n} resume(s) visible")


def cmd_list(a):
    q = {}
    if a.tag:
        q["tags"] = a.tag
    path = "/resumes" + ("?" + urllib.parse.urlencode(q) if q else "")
    status, payload = request("GET", path)
    ok_or_die(status, payload, "list")
    if a.search and isinstance(payload, list):
        s = a.search.lower()
        payload = [r for r in payload if s in json.dumps(r).lower()]
    out_json(payload)


def fetch_resume(rid):
    status, payload = request("GET", f"/resumes/{rid}")
    ok_or_die(status, payload, "get resume")
    return payload


def cmd_get(a):
    res = fetch_resume(a.id)
    if a.out:
        write_private_file(Path(a.out), json.dumps(res, indent=2, ensure_ascii=False))
        print(f"wrote {a.out}")
    else:
        out_json(res)


def save_backup(rid, res):
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(BACKUP_DIR, 0o700)
    except OSError:
        pass
    p = BACKUP_DIR / f"{rid}-{time.strftime('%Y%m%d-%H%M%S')}-{time.time_ns() % 1_000_000_000:09d}.json"
    write_private_file(p, json.dumps(res, indent=2, ensure_ascii=False))
    return p


def cmd_backup(a):
    print("saved", save_backup(a.id, fetch_resume(a.id)))


def load_ops(src):
    raw = sys.stdin.read() if src == "-" else Path(src).read_text()
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError as e:
        die(f"operations file is not valid JSON: {e}")
    ops = obj.get("operations") if isinstance(obj, dict) else obj
    if not isinstance(ops, list) or not ops:
        die("operations must be a non-empty JSON array (or {\"operations\": [...]})")
    for i, op in enumerate(ops):
        if op.get("op") not in {"add", "remove", "replace", "move", "copy", "test"}:
            die(f"operation {i}: bad or missing 'op'")
        if "path" not in op:
            die(f"operation {i}: missing 'path'")
    return ops


def cmd_patch(a):
    ops = load_ops(a.ops)
    res = fetch_resume(a.id)
    if res.get("isLocked"):
        die("resume is locked. Unlock it first (`rr.py unlock ID`) - only with the owner's OK.")
    if a.dry_run:
        print(f"DRY RUN against '{res.get('name')}' (updatedAt {res.get('updatedAt')}). Not sent:")
        out_json(ops)
        return
    if not a.no_backup:
        print("backup:", save_backup(a.id, res), file=sys.stderr)
    body = {"operations": ops}
    if not a.no_lock:
        if not res.get("updatedAt"):
            die("resume has no updatedAt to guard the write; pass --no-lock to skip the check")
        body["expectedUpdatedAt"] = res["updatedAt"]
    status, payload = request("PATCH", f"/resumes/{a.id}", body)
    ok_or_die(status, payload, "patch")
    print(f"patched '{payload.get('name', a.id)}' - new updatedAt {payload.get('updatedAt')}")


def cmd_put(a):
    try:
        body = json.loads(a.json)
    except json.JSONDecodeError as e:
        die(f"--json is not valid JSON: {e}")
    status, payload = request("PUT", f"/resumes/{a.id}", body)
    ok_or_die(status, payload, "put")
    out_json(payload)


def cmd_lock(a):
    locked = a.cmd == "lock"
    status, payload = request("POST", f"/resumes/{a.id}/lock", {"isLocked": locked})
    ok_or_die(status, payload, a.cmd)
    print(f"{a.cmd}ed {a.id}")


def cmd_export(a):
    status, raw = request("GET", f"/resumes/{a.id}/exports/{a.format}", expect_binary=True)
    if status >= 400:
        ok_or_die(status, raw, "export")
    write_private_file(Path(a.out), raw if isinstance(raw, bytes) else json.dumps(raw).encode())
    print(f"wrote {a.out} ({a.format})")


def cmd_request(a):
    body = None
    if a.body:
        body = json.loads(Path(a.body[1:]).read_text() if a.body.startswith("@") else a.body)
    path = a.path if a.path.startswith("/") else "/" + a.path
    status, payload = request(a.method.upper(), path, body)
    print(f"HTTP {status}", file=sys.stderr)
    out_json(payload) if not isinstance(payload, str) else print(payload)
    sys.exit(0 if status < 400 else 1)


def main():
    p = argparse.ArgumentParser(description="Self-hosted Reactive Resume helper", formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    sp = p.add_subparsers(dest="cmd", required=True)

    c = sp.add_parser("config"); c.add_argument("action", choices=["set", "show", "clear"])
    c.add_argument("--url"); c.add_argument("--key")
    c.add_argument("--insecure", action="store_true", help="skip TLS verification (self-signed certs)")
    c.set_defaults(fn=cmd_config)

    sp.add_parser("check").set_defaults(fn=cmd_check)

    c = sp.add_parser("list"); c.add_argument("--tag"); c.add_argument("--search"); c.set_defaults(fn=cmd_list)
    c = sp.add_parser("get"); c.add_argument("id"); c.add_argument("--out"); c.set_defaults(fn=cmd_get)
    c = sp.add_parser("backup"); c.add_argument("id"); c.set_defaults(fn=cmd_backup)

    c = sp.add_parser("patch"); c.add_argument("id"); c.add_argument("--ops", required=True)
    c.add_argument("--dry-run", action="store_true")
    c.add_argument("--no-lock", action="store_true", help="skip the expectedUpdatedAt conflict guard")
    c.add_argument("--no-backup", action="store_true")
    c.set_defaults(fn=cmd_patch)

    c = sp.add_parser("put"); c.add_argument("id"); c.add_argument("--json", required=True); c.set_defaults(fn=cmd_put)
    for name in ("lock", "unlock"):
        c = sp.add_parser(name); c.add_argument("id"); c.set_defaults(fn=cmd_lock)

    c = sp.add_parser("export"); c.add_argument("id")
    c.add_argument("--format", required=True, choices=["pdf", "docx", "markdown", "json"])
    c.add_argument("--out", required=True); c.set_defaults(fn=cmd_export)

    c = sp.add_parser("request"); c.add_argument("method"); c.add_argument("path"); c.add_argument("--body")
    c.set_defaults(fn=cmd_request)

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
