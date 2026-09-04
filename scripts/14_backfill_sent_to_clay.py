#!/usr/bin/env python3
"""
Step 14: record which companies were actually sent to Clay.

outbound_companies_scored.sent_to_clay_at has existed since the schema was
written and nothing has ever filled it: null on all 830 rows. Without it the
funnel cannot tell a row Clay never saw from a row Clay saw and returned nothing
for, so it called all 784 of them never_sent_to_clay, and 34 of those had been
sent. A stage that reports a lie is worse than a stage that is missing.

The only record of what was uploaded is the export file itself. Its 50 CIKs are
identical to the set in clay_payload-enriched.csv that came back, which is what
proves it is the file that went.

Reads:  exports/clay_payload_<date>_top50.csv (the file that was uploaded)
Writes: outbound_companies_scored.sent_to_clay_at
Cost:   nothing. A file and a database.

The timestamp is the export's own date, not now(). Stamping today would say the
rows were sent today, which is a fact this script does not have and would be
inventing.

Idempotent: it writes the same date every time, so re-running changes nothing.
It refuses to run if a row already carries a DIFFERENT date, because that would
mean a second Clay run happened and this file is no longer the whole record.

Usage:
    py -3 scripts/14_backfill_sent_to_clay.py
    py -3 scripts/14_backfill_sent_to_clay.py --dry-run
"""
import os
import re
import csv
import sys
import glob

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
    for k in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"):
        if not env.get(k):
            sys.exit("%s is not set in .env" % k)
    return env


def read_ciks(path):
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return {int(r["cik"]) for r in csv.DictReader(fh) if r.get("cik", "").strip()}


ENV = load_env()
DRY = "--dry-run" in sys.argv[1:]

SB = httpx.Client(
    base_url=ENV["SUPABASE_URL"].rstrip("/") + "/rest/v1/",
    headers={"apikey": ENV["SUPABASE_SERVICE_ROLE_KEY"],
             "Authorization": "Bearer " + ENV["SUPABASE_SERVICE_ROLE_KEY"],
             "Content-Type": "application/json"},
    timeout=120.0,
)

# The uploaded file is the newest top50 export. Its date is the send date.
uploads = sorted(glob.glob(os.path.join(ROOT, "exports", "clay_payload_*_top50.csv")))
if not uploads:
    sys.exit("no exports/clay_payload_<date>_top50.csv found. Nothing to backfill from.")
upload = uploads[-1]
m = re.search(r"clay_payload_(\d{4}-\d{2}-\d{2})_top50\.csv$", os.path.basename(upload))
if not m:
    sys.exit("cannot read a date out of %s" % os.path.basename(upload))
sent_date = m.group(1)
sent_at = sent_date + "T00:00:00+00:00"

sent = read_ciks(upload)
print("uploaded file  %s" % os.path.basename(upload))
print("send date      %s" % sent_date)
print("rows           %d" % len(sent))

# The returned file must describe the same companies, or this is not the file
# that went to Clay and the backfill would be stamping the wrong rows.
returned_path = os.path.join(ROOT, "exports", "clay_payload-enriched.csv")
if os.path.exists(returned_path):
    returned = read_ciks(returned_path)
    if returned != sent:
        sys.exit("the returned file names %d companies the uploaded one does not, and misses %d. "
                 "These are not the same run." % (len(returned - sent), len(sent - returned)))
    print("returned file  matches the uploaded one, company for company")

r = SB.get("outbound_companies_scored",
           params={"select": "cik,sent_to_clay_at", "sent_to_clay_at": "not.is.null"})
r.raise_for_status()
already = {row["cik"]: row["sent_to_clay_at"] for row in r.json()}
conflict = {c: d for c, d in already.items() if not str(d).startswith(sent_date)}
if conflict:
    sys.exit("%d row(s) already carry a different send date, e.g. cik %s -> %s. A second Clay run "
             "happened and this export is no longer the whole record."
             % (len(conflict), *list(conflict.items())[0]))

todo = sorted(sent - set(already))
print("already stamped %d, to write %d" % (len(already), len(todo)))

if todo and not DRY:
    for i in range(0, len(todo), 25):
        chunk = todo[i:i + 25]
        p = SB.patch("outbound_companies_scored",
                     params={"cik": "in.(%s)" % ",".join(str(c) for c in chunk)},
                     headers={"Prefer": "return=representation"},
                     json={"sent_to_clay_at": sent_at})
        p.raise_for_status()
        if len(p.json()) != len(chunk):
            sys.exit("patched %d rows, expected %d" % (len(p.json()), len(chunk)))

print()
print("VERIFICATION")
def count(**params):
    r = SB.get("outbound_companies_scored",
               params=dict(params, select="cik"),
               headers={"Prefer": "count=exact", "Range": "0-0"})
    r.raise_for_status()
    return int(r.headers["content-range"].split("/")[-1])

n_sent = count(sent_to_clay_at="not.is.null")
n_back = count(sent_to_clay_at="not.is.null", returned_from_clay_at="not.is.null")
n_empty = count(sent_to_clay_at="not.is.null", returned_from_clay_at="is.null")
n_never = count(sent_to_clay_at="is.null")
n_signer = count(sent_to_clay_at="is.null", dedupe_status="eq.dupe_same_signer")
print("  sent to Clay                    %d%s" % (n_sent, "  (dry run)" if DRY else ""))
print("    returned something            %d" % n_back)
print("    returned nothing              %d" % n_empty)
print("  never sent                      %d" % n_never)
print("    of those, held back on signer %d" % n_signer)
print("    of those, free tier           %d" % (n_never - n_signer))
if not DRY:
    if n_sent != len(sent):
        sys.exit("expected %d rows stamped, found %d" % (len(sent), n_sent))
    total = count()
    if n_sent + n_never != total:
        sys.exit("%d + %d does not equal %d scored rows" % (n_sent, n_never, total))
    print()
    print("  %d + %d = %d, every scored row is on one side or the other."
          % (n_sent, n_never, total))
