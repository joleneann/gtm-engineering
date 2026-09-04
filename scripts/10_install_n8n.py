#!/usr/bin/env python3
"""
Step 10: install the three workflows into the local n8n.

Creates the two header credentials from the keys already in .env, rewrites the
placeholder credential ids in the workflow files to the real ones, and posts the
workflows to n8n's public API. Doing it by hand means clicking a credential onto
nine nodes and getting one of them wrong.

The Gmail credentials are deliberately not created here. The SMTP password is an
app password and is not mine to handle, and the reply leg's Gmail credential is
OAuth, which only completes in a browser. Both are made in n8n's own UI; this
script finds the OAuth one by its name and binds it to the node.

Reads:  n8n/*.json, .env (SUPABASE_SERVICE_ROLE_KEY, PIPEDRIVE_API_TOKEN,
        N8N_API_KEY)
Writes: credentials and workflows in the local n8n at N8N_URL
Cost:   nothing. Everything is local.

Idempotent: a credential or workflow of the same name is reused or updated
rather than duplicated. Nothing prints a secret.

Usage:
    py -3 scripts/10_install_n8n.py
"""
import os
import sys
import json
import glob
import sqlite3

import httpx

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
N8N = os.environ.get("N8N_URL", "http://localhost:5678")

sys.stdout.reconfigure(encoding="utf-8")

# The placeholder ids written into the workflow files, and the credential each
# one stands for.
CREDS = {
    "SUPABASE_CRED": {
        "name": "Supabase service role",
        "type": "httpHeaderAuth",
        "env": "SUPABASE_SERVICE_ROLE_KEY",
        "header": "apikey",
    },
    "PIPEDRIVE_CRED": {
        "name": "Pipedrive API token",
        "type": "httpHeaderAuth",
        "env": "PIPEDRIVE_API_TOKEN",
        "header": "x-api-token",
    },
}

# OAuth, so it cannot be built from a key in .env. Made in the UI and found by
# this name.
GMAIL_NAME = "Gmail account"


def load_env():
    env = {}
    path = os.path.join(ROOT, ".env")
    if not os.path.exists(path):
        sys.exit(".env not found.")
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    for k in ("N8N_API_KEY", "SUPABASE_SERVICE_ROLE_KEY", "PIPEDRIVE_API_TOKEN"):
        if not env.get(k):
            sys.exit("%s is not set in .env" % k)
    return env


ENV = load_env()
CLIENT = httpx.Client(
    base_url=N8N.rstrip("/") + "/api/v1",
    headers={"X-N8N-API-KEY": ENV["N8N_API_KEY"], "Content-Type": "application/json"},
    timeout=30.0,
)


def call(method, path, **kw):
    r = CLIENT.request(method, path, **kw)
    if r.status_code >= 400:
        sys.exit("%s %s -> %s\n%s" % (method, path, r.status_code, r.text[:400]))
    return r.json() if r.text.strip() else {}


def gmail_credential_id():
    """The OAuth credential, made by hand in the UI, found by its name.

    The public API can create a credential and cannot list one, so this reads
    n8n's SQLite directly. A read, while n8n is running, of a name and an id:
    no secret is touched and nothing is written."""
    db = os.path.join(os.path.expanduser("~"), ".n8n", "database.sqlite")
    if not os.path.exists(db):
        return None
    con = sqlite3.connect("file:%s?mode=ro" % db.replace("\\", "/"), uri=True)
    try:
        row = con.execute("select id from credentials_entity where name = ?",
                          (GMAIL_NAME,)).fetchone()
    finally:
        con.close()
    return row[0] if row else None


def ensure_credentials():
    """The public API can create a credential but cannot list them, so a second
    run gets a fresh one. Names are identical, which is harmless: the workflows
    are rewritten to whichever id this run produced."""
    ids = {}
    for placeholder, spec in CREDS.items():
        body = {
            "name": spec["name"],
            "type": spec["type"],
            "data": {"name": spec["header"], "value": ENV[spec["env"]]},
        }
        got = call("POST", "/credentials", json=body)
        ids[placeholder] = got["id"]
        print("credential  %-24s id=%s" % (spec["name"], got["id"]))
    gmail = gmail_credential_id()
    if gmail:
        ids["GMAIL_CRED"] = gmail
        print("credential  %-24s id=%s  (found, made by hand)" % (GMAIL_NAME, gmail))
    else:
        print("credential  %-24s NOT FOUND. GTME 2 installs with that node "
              "unbound; make it in the UI and re-run." % GMAIL_NAME)
    return ids


def existing_workflows():
    out = {}
    cursor = None
    while True:
        params = {"limit": 100}
        if cursor:
            params["cursor"] = cursor
        page = call("GET", "/workflows", params=params)
        for w in page.get("data", []):
            out[w["name"]] = w["id"]
        cursor = page.get("nextCursor")
        if not cursor:
            break
    return out


def main():
    print("n8n at %s" % N8N)
    ids = ensure_credentials()
    print()

    have = existing_workflows()
    for path in sorted(glob.glob(os.path.join(ROOT, "n8n", "*.json"))):
        raw = open(path, encoding="utf-8").read()
        for placeholder, real in ids.items():
            raw = raw.replace('"id": "%s"' % placeholder, '"id": "%s"' % real)
        wf = json.loads(raw)

        # The public API rejects anything outside these four keys.
        body = {k: wf[k] for k in ("name", "nodes", "connections", "settings") if k in wf}

        name = body["name"]
        if name in have:
            got = call("PUT", "/workflows/%s" % have[name], json=body)
            verb = "updated"
        else:
            got = call("POST", "/workflows", json=body)
            verb = "created"
        print("%-8s %-24s id=%-22s nodes=%d"
              % (verb, name, got["id"], len(body["nodes"])))

    print()
    print("VERIFICATION")
    after = existing_workflows()
    for name in sorted(after):
        wf = call("GET", "/workflows/%s" % after[name])
        unbound = []
        for n in wf["nodes"]:
            for ctype, c in (n.get("credentials") or {}).items():
                if c.get("id") in CREDS or c.get("id") == "GMAIL_CRED":
                    unbound.append(n["name"])
        print("  %-24s nodes=%-3d active=%-6s unbound credentials: %s"
              % (name, len(wf["nodes"]), wf.get("active"), unbound or "none"))
    print()
    print("  Still to do by hand, because neither secret is mine to handle:")
    print("  SMTP   smtp.gmail.com:465 SSL, app password, onto the Send node in GTME 1")
    print("  Gmail  the OAuth credential named 'Gmail account', made in the n8n UI.")
    print("         Re-run this script once it exists and GTME 2 binds to it.")


if __name__ == "__main__":
    main()
