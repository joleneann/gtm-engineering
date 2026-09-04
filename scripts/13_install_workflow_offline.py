#!/usr/bin/env python3
"""
Step 13: install a workflow file into n8n's database with n8n stopped.

The public API cannot be relied on for the reply workflow. While its trigger is
active the process is busy enough that API requests time out, and the trigger is
active from the moment n8n boots. Writing the database directly is the only way
to change a workflow that misbehaves on startup.

Reads:  the workflow JSON named on the command line
Writes: workflow_entity in ~/.n8n/database.sqlite, after a timestamped backup
Cost:   nothing.

Matched by name, so it replaces rather than duplicates. The workflow files carry
placeholder credential ids (SUPABASE_CRED, PIPEDRIVE_CRED, GMAIL_CRED), which are
resolved here against credentials_entity by the credential's NAME, so no real id
and no secret is ever committed. A file naming a credential this n8n does not
have stops the run, because a workflow that imports with an unbound credential
looks correct and then fails on the node.

Workflows are installed deactivated. Activating a trigger is a deliberate act.

n8n MUST be stopped. The script refuses to run while the port is answering.

Usage:
    py -3 scripts/13_install_workflow_offline.py n8n/wf2_reply_catcher.json
"""
import os
import sys
import json
import shutil
import socket
import sqlite3
import datetime as dt
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(os.path.expanduser("~"), ".n8n", "database.sqlite")

sys.stdout.reconfigure(encoding="utf-8")


def port_open(host="127.0.0.1", port=5678):
    s = socket.socket()
    s.settimeout(1.5)
    try:
        s.connect((host, port))
        return True
    except OSError:
        return False
    finally:
        s.close()


if len(sys.argv) < 2:
    sys.exit(__doc__.strip().splitlines()[-1])
path = sys.argv[1]
if not os.path.isabs(path):
    path = os.path.join(ROOT, path)
if not os.path.exists(path):
    sys.exit("not found: %s" % path)
if port_open():
    sys.exit("n8n is still running on 5678. Stop it first: this edits its database.")

wf = json.load(open(path, encoding="utf-8"))
name = wf["name"]

backup = DB + ".bak-" + dt.datetime.now().strftime("%Y%m%d-%H%M%S")
shutil.copy2(DB, backup)
print("backup   %s" % os.path.basename(backup))

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
cur = con.cursor()

# Every credential the file names must exist, or the workflow imports looking
# correct and fails on the node at run time. The file names it by the display
# name beside a placeholder id, and the id is looked up here: committing a real
# id would tie the file to one installation, and the ids are not secrets but
# they are not portable either.
have = {r["id"]: r["name"] for r in cur.execute("select id, name from credentials_entity")}
by_name = {}
for cid, cname in have.items():
    by_name.setdefault(cname, cid)
for n in wf["nodes"]:
    for ctype, cred in (n.get("credentials") or {}).items():
        if cred.get("id") in have:
            continue
        real = by_name.get(cred.get("name"))
        if not real:
            sys.exit("node %r wants the credential named %r, which this n8n does "
                     "not have. Create it in the UI first."
                     % (n["name"], cred.get("name")))
        cred["id"] = real

# Every connection endpoint must name a node that exists. A rename that misses
# the connections column shows only as "invalid workflow structure" in the UI.
names = {n["name"] for n in wf["nodes"]}
for src, outs in wf["connections"].items():
    if src not in names:
        sys.exit("connection source %r is not a node" % src)
    for branch in outs.get("main", []):
        for link in branch or []:
            if link["node"] not in names:
                sys.exit("connection target %r is not a node" % link["node"])

row = cur.execute("select id from workflow_entity where name = ?", (name,)).fetchone()
now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
version = str(uuid.uuid4())
nodes = json.dumps(wf["nodes"])
conns = json.dumps(wf["connections"])
settings = json.dumps(wf.get("settings", {"executionOrder": "v1"}))

if row:
    cur.execute(
        "update workflow_entity set nodes = ?, connections = ?, settings = ?, "
        "active = 0, versionId = ?, updatedAt = ? where id = ?",
        (nodes, conns, settings, version, now, row["id"]))
    print("replaced %s (id=%s)" % (name, row["id"]))
else:
    sys.exit("no workflow named %r exists. Create it through the API first." % name)

con.commit()

print()
print("VERIFICATION")
r = cur.execute("select name, active, nodes, connections from workflow_entity "
                "where name = ?", (name,)).fetchone()
back = json.loads(r["nodes"])
print("  %-24s active=%-5s nodes=%d" % (r["name"], bool(r["active"]), len(back)))
for n in back:
    creds = ", ".join("%s=%s" % (t, have[c["id"]]) for t, c in (n.get("credentials") or {}).items())
    print("    %-22s %-38s %s" % (n["name"], n["type"], creds))
con.close()
print()
print("  start n8n with ./run_n8n.sh, then press Execute on the workflow")
