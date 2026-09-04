#!/usr/bin/env python3
"""
Step 12: patch the n8n workflows directly in its database, with n8n stopped.

The public API cannot be used for this. The reply workflow is activated at
startup, its IMAP node immediately starts downloading every unread message in
the mailbox, and that saturates the event loop before any API request is
answered. The fix has to be applied while nothing is running.

Three changes:

1. GTME 1's send guard checks the TEST_EMAILS allowlist rather than one
   hardcoded address, because each test row now has its own inbox.
2. GTME 2 matches a reply on the sender, which is what production does. It only
   ever needed the subject because both test rows shared one mailbox.
3. GTME 2's Inbox node reads mail that is unread AND received today. Unfiltered
   it pulls the whole archive: that is what took the process to a 2 GB heap and
   aborted it before the reply arrived.

GTME 2 is also left deactivated. Activating it is a deliberate act now, not
something that happens the moment n8n boots.

Reads:  ~/.n8n/database.sqlite, .env
Writes: the same database, after taking a timestamped backup beside it
Cost:   nothing.

n8n MUST be stopped first. The script refuses to run if the port is answering.

Usage:
    py -3 scripts/12_patch_n8n_db.py
"""
import os
import sys
import json
import shutil
import socket
import sqlite3
import datetime as dt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(os.path.expanduser("~"), ".n8n", "database.sqlite")

sys.stdout.reconfigure(encoding="utf-8")


def load_env():
    env = {}
    path = os.path.join(ROOT, ".env")
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    if not env.get("TEST_EMAILS"):
        sys.exit("TEST_EMAILS is not set in .env")
    return env


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


if port_open():
    sys.exit("n8n is still running on 5678. Stop it first: this edits its database.")
if not os.path.exists(DB):
    sys.exit("not found: %s" % DB)

ENV = load_env()
ALLOW = [a.strip().lower() for a in ENV["TEST_EMAILS"].split(",") if a.strip()]
TODAY = dt.date.today().strftime("%B %d, %Y")

backup = DB + ".bak-" + dt.datetime.now().strftime("%Y%m%d-%H%M%S")
shutil.copy2(DB, backup)
print("backup      %s" % os.path.basename(backup))

CODE = r"""// The sender is what ties a reply back to a row: an address belongs to one
// person, so the match is exact. Each test row has its own inbox for exactly
// this reason; two rows sharing an address make the match ambiguous.
//
// The IMAP node puts the sender under metadata.from with the simple format and
// under from with others, so every shape is checked rather than one assumed.
// "Travis <travis@atoms.co>" has to become travis@atoms.co.
const out = [];
for (const item of $input.all()) {
  const j = item.json || {};
  const raw = j.from
    || (j.metadata && (j.metadata.from || j.metadata.From))
    || (j.headers && (j.headers.from || j.headers.From))
    || '';
  const m = String(raw).match(/[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}/);
  if (!m) {
    throw new Error('No sender address on the message. Keys: ' + Object.keys(j).join(', '));
  }
  out.push({ json: { from_email: m[0].toLowerCase() } });
}
return out;"""

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
cur = con.cursor()

rows = cur.execute("select id, name, active, nodes from workflow_entity").fetchall()
print("workflows   %d" % len(rows))

changed = 0
for row in rows:
    nodes = json.loads(row["nodes"])
    touched = []

    if row["name"].startswith("GTME 1"):
        for n in nodes:
            if n["name"].startswith("Recipient must be"):
                n["parameters"]["conditions"]["conditions"] = [{
                    "id": "c2",
                    "leftValue": "={{ %s.includes($('Fetch dispatchable')"
                                 ".item.json.work_email) }}" % json.dumps(ALLOW),
                    "rightValue": True,
                    "operator": {"type": "boolean", "operation": "true",
                                 "singleValue": True},
                }]
                n["notes"] = ("The compliance rule. The only sendable addresses are "
                              "the test inboxes; anything else breaks the run rather "
                              "than sending.")
                touched.append(n["name"])

    if row["name"].startswith("GTME 2"):
        for n in nodes:
            if n["name"] in ("Sender address", "Sender and subject"):
                n["name"] = "Sender address"
                n["parameters"]["jsCode"] = CODE
                touched.append(n["name"])
            elif n["name"] == "Inbox":
                n["parameters"]["mailbox"] = "INBOX"
                n["parameters"]["postProcessAction"] = "read"
                n["parameters"]["format"] = "simple"
                n["parameters"]["downloadAttachments"] = False
                n["parameters"]["options"] = {
                    "customEmailConfig": '["UNSEEN", ["SINCE", "%s"]]' % TODAY,
                    "forceReconnect": 60,
                }
                n["notes"] = ("Unread AND received today. Unfiltered this pulls every "
                              "unread message in the mailbox: on a personal Gmail that "
                              "is years of it, and the process died at a 2 GB heap "
                              "before the reply ever arrived.")
                touched.append(n["name"])
            elif n["name"] == "Find the deal":
                p = n["parameters"]["queryParameters"]["parameters"]
                p[:] = [x for x in p if x["name"] not in ("or", "work_email")]
                p.insert(1, {"name": "work_email", "value": "=eq.{{ $json.from_email }}"})
                n["notes"] = ("Sender, and crm_stage = emailed, so only a reply to "
                              "something actually sent moves a deal.")
                touched.append(n["name"])

    if not touched:
        continue

    blob = json.dumps(nodes).replace("Sender and subject", "Sender address")
    if row["name"].startswith("GTME 2"):
        # Deactivated on purpose: activating the IMAP trigger is now a deliberate
        # act, not something that happens the moment n8n boots.
        cur.execute("update workflow_entity set nodes = ?, active = 0 where id = ?",
                    (blob, row["id"]))
    else:
        cur.execute("update workflow_entity set nodes = ? where id = ?",
                    (blob, row["id"]))
    changed += 1
    print("patched     %-24s %s" % (row["name"], ", ".join(sorted(set(touched)))))

con.commit()

print()
print("VERIFICATION")
for row in cur.execute("select name, active, nodes from workflow_entity order by name"):
    nodes = json.loads(row["nodes"])
    print("  %-24s active=%-5s nodes=%d" % (row["name"], bool(row["active"]), len(nodes)))
    if row["name"].startswith("GTME 2"):
        inbox = next(n for n in nodes if n["name"] == "Inbox")
        find = next(n for n in nodes if n["name"] == "Find the deal")
        print("      inbox filter : %s" % inbox["parameters"]["options"]["customEmailConfig"])
        print("      lookup       : %s"
              % [x["value"] for x in find["parameters"]["queryParameters"]["parameters"]])
        assert row["active"] == 0, "GTME 2 must not start activated"
    if row["name"].startswith("GTME 1"):
        g = next(n for n in nodes if n["name"].startswith("Recipient"))
        print("      guard        : %s"
              % g["parameters"]["conditions"]["conditions"][0]["leftValue"])
    for n in nodes:
        if n["type"].endswith(("httpRequest", "emailReadImap", "emailSend")) \
                and not n.get("credentials"):
            print("      NO CREDENTIAL on %s" % n["name"])

con.close()
print()
print("  %d workflow(s) changed. Start n8n with ./run_n8n.sh" % changed)
