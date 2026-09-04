#!/usr/bin/env python3
"""
Read-only probe of the Pipedrive account, run once after the CRM is set up by hand.

Confirms the token authenticates, prints the pipeline and its stages, and lists
every custom field with its API key. Pipedrive addresses a custom field by a
40-character hash, never by its display name, so nothing can be written into one
until that map exists. The map is archived under docs/sources/ so the n8n step
reads it instead of re-fetching.

Reads:  PIPEDRIVE_API_TOKEN from .env
Writes: docs/sources/pipedrive_fields_<date>.md
Cost:   nothing. Every call is a GET.

The token goes in a header, never a query parameter: a token in a URL ends up in
logs. Nothing here prints it.

Usage:
    py -3 scripts/09_pipedrive_probe.py
"""
import os
import sys
import datetime as dt

import httpx

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://api.pipedrive.com/api/v1"


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
    if not env.get("PIPEDRIVE_API_TOKEN"):
        sys.exit("PIPEDRIVE_API_TOKEN is not set in .env")
    return env


ENV = load_env()
CLIENT = httpx.Client(
    base_url=BASE,
    headers={"x-api-token": ENV["PIPEDRIVE_API_TOKEN"], "Accept": "application/json"},
    timeout=30.0,
)


def get(path):
    r = CLIENT.get(path)
    if r.status_code != 200:
        sys.exit("GET %s -> %s\n%s" % (path, r.status_code, r.text[:400]))
    body = r.json()
    if not body.get("success", False):
        sys.exit("GET %s returned success=false\n%s" % (path, str(body)[:400]))
    return body.get("data") or []


def custom(fields):
    """Only the fields added by hand. Pipedrive's own fields have short string
    keys; a custom field's key is a 40-character hex hash."""
    out = []
    for f in fields:
        key = f.get("key", "")
        if len(key) == 40 and all(c in "0123456789abcdef" for c in key):
            out.append((f["name"], f.get("field_type", "?"), key))
    return sorted(out)


me = get("/users/me")
print("connected as   : %s" % me.get("name"))
print("company domain : %s" % me.get("company_domain"))
print()

pipelines = get("/pipelines")
stages = get("/stages")
for p in pipelines:
    print("pipeline %s: %s" % (p["id"], p["name"]))
    rows = sorted([x for x in stages if x["pipeline_id"] == p["id"]],
                  key=lambda x: x["order_nr"])
    for s in rows:
        print("    %2d  %-14s  stage_id=%s" % (s["order_nr"], s["name"], s["id"]))
print()

groups = [("organization", get("/organizationFields")),
          ("person", get("/personFields")),
          ("deal", get("/dealFields"))]

lines = ["# Pipedrive field map",
         "",
         "Fetched %s by `scripts/09_pipedrive_probe.py`." % dt.date.today(),
         "Pipedrive addresses a custom field by its 40-character key, never by its",
         "display name. This is that map, and it is what the n8n step writes to.",
         ""]

for name, fields in groups:
    cf = custom(fields)
    print("%s: %d custom field(s)" % (name, len(cf)))
    lines += ["## %s" % name, "", "| Field | Type | API key |", "|---|---|---|"]
    for fname, ftype, key in cf:
        print("    %-18s %-12s %s" % (fname, ftype, key))
        lines.append("| %s | %s | `%s` |" % (fname, ftype, key))
    lines.append("")

lines += ["## Stages", "", "| Pipeline | # | Stage | stage_id |", "|---|---|---|---|"]
for p in pipelines:
    rows = sorted([x for x in stages if x["pipeline_id"] == p["id"]],
                  key=lambda x: x["order_nr"])
    for s in rows:
        lines.append("| %s | %d | %s | %s |" % (p["name"], s["order_nr"], s["name"], s["id"]))
lines.append("")

path = os.path.join(ROOT, "docs", "sources", "pipedrive_fields_%s.md" % dt.date.today())
with open(path, "w", encoding="utf-8", newline="\n") as fh:
    fh.write("\n".join(lines))
print()
print("wrote docs/sources/pipedrive_fields_%s.md" % dt.date.today())
