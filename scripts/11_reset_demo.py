#!/usr/bin/env python3
"""
Step 11: put the CRM leg back to the state it was in before the first run.

The demo is meant to be run more than once, on camera, and a second run of the
outbound workflow must not append a second set of deals to the first. Deleting
by hand in the Pipedrive UI leaves the ids in Supabase pointing at objects that
no longer exist, which is worse than not resetting at all.

Reads:  outbound_companies_scored, Pipedrive
Writes: deletes every Pipedrive activity, deal, person and organization; clears
        the CRM columns in Supabase; removes non-seed rows from contacted_emails
Cost:   nothing.

Deletion order is activities, deals, persons, organizations. Pipedrive refuses
to delete a parent while a child points at it.

Seeded rows in contacted_emails are kept: they are what makes
dupe_already_emailed fire, and this reset is about the run, not the seeds.

Usage:
    py -3 scripts/11_reset_demo.py
    py -3 scripts/11_reset_demo.py --dry-run
"""
import os
import sys

import httpx

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")


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
    for k in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "PIPEDRIVE_API_TOKEN"):
        if not env.get(k):
            sys.exit("%s is not set in .env" % k)
    return env


ENV = load_env()
DRY = "--dry-run" in sys.argv[1:]

SB = httpx.Client(
    base_url=ENV["SUPABASE_URL"].rstrip("/") + "/rest/v1/",
    headers={"apikey": ENV["SUPABASE_SERVICE_ROLE_KEY"],
             "Authorization": "Bearer " + ENV["SUPABASE_SERVICE_ROLE_KEY"],
             "Content-Type": "application/json"},
    timeout=60.0,
)
PD = httpx.Client(
    base_url="https://api.pipedrive.com/api/v1",
    headers={"x-api-token": ENV["PIPEDRIVE_API_TOKEN"]},
    timeout=60.0,
)


def pd_all(resource):
    out, start = [], 0
    while True:
        r = PD.get("/" + resource, params={"limit": 100, "start": start})
        r.raise_for_status()
        body = r.json()
        out.extend(body.get("data") or [])
        more = (body.get("additional_data") or {}).get("pagination") or {}
        if not more.get("more_items_in_collection"):
            break
        start = more["next_start"]
    return out


def wipe(resource):
    items = pd_all(resource)
    for it in items:
        if DRY:
            continue
        r = PD.delete("/%s/%s" % (resource, it["id"]))
        if r.status_code >= 400:
            sys.exit("DELETE %s/%s -> %s\n%s" % (resource, it["id"], r.status_code, r.text[:300]))
    print("  %-16s deleted %d%s" % (resource, len(items), "  (dry run)" if DRY else ""))
    return len(items)


print("PIPEDRIVE")
# Children first: Pipedrive refuses to delete a parent while a child points at it.
for res in ("activities", "deals", "persons", "organizations"):
    wipe(res)

print()
print("SUPABASE")
r = SB.get("outbound_companies_scored",
           params={"select": "cik", "pipedrive_deal_id": "not.is.null"})
r.raise_for_status()
n = len(r.json())
if not DRY and n:
    p = SB.patch("outbound_companies_scored",
                 params={"pipedrive_deal_id": "not.is.null"},
                 headers={"Prefer": "return=representation"},
                 json={"pipedrive_org_id": None, "pipedrive_person_id": None,
                       "pipedrive_deal_id": None, "pipedrive_synced_at": None,
                       "sent_at": None, "replied_at": None, "held_until": None,
                       "crm_stage": None})
    p.raise_for_status()
    if len(p.json()) != n:
        sys.exit("cleared %d rows, expected %d" % (len(p.json()), n))
print("  scored rows cleared   %d%s" % (n, "  (dry run)" if DRY else ""))

r = SB.get("contacted_emails", params={"select": "email_normalised", "is_demo_seed": "is.false"})
r.raise_for_status()
m = len(r.json())
if not DRY and m:
    d = SB.delete("contacted_emails", params={"is_demo_seed": "is.false"})
    d.raise_for_status()
print("  contacted_emails, non-seed rows removed  %d%s" % (m, "  (dry run)" if DRY else ""))

if DRY:
    sys.exit(0)

print()
print("VERIFICATION")
for res in ("activities", "deals", "persons", "organizations"):
    left = pd_all(res)
    print("  pipedrive %-16s %d" % (res, len(left)))
    if left:
        sys.exit("%s still holds %d rows" % (res, len(left)))
left = SB.get("outbound_companies_scored",
              params={"select": "cik", "or": "(pipedrive_deal_id.not.is.null,"
                                              "sent_at.not.is.null,crm_stage.not.is.null)"}).json()
print("  scored rows with CRM state    %d" % len(left))
if left:
    sys.exit("%d scored rows still carry CRM state" % len(left))
seeds = SB.get("contacted_emails", params={"select": "email_normalised"}).json()
print("  contacted_emails rows kept    %d (the seed)" % len(seeds))
print()
print("  clean. Re-run the outbound workflow and it starts from nothing.")
