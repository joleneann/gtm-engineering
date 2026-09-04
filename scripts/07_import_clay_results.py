#!/usr/bin/env python3
"""
Step 7: bring Clay's return home into outbound_companies_scored.

n8n reads Supabase, never Clay and never a CSV, so the enrichment has to land in
the table before the CRM leg can run.

Reads:  exports/clay_payload-enriched.csv
Writes: outbound_companies_scored (domain, work_email, copy_body, subject,
        contact_name, contact_title, returned_from_clay_at, enrichment_status)
Cost:   nothing. Clay has already run; this is a file and a database.

Domain comes from claygent_domain and the address from final_email_validated.
Nothing else in the CSV is read. The Find Work Email waterfall also emits a
domain, and on the 16 resolved rows it disagreed with Claygent five times and was
wrong every time: polsinelli.com is Tabnam's law firm, preqin.com is a data
vendor, yahoo.com is nobody's company. Claygent covered all 16 by itself, so the
waterfall adds no coverage and only offers filing-agent domains.

contact_name is rewritten from Clay's split column, dropping the ", Title" that
04_score.py joined on. The title lands in its own column instead of being thrown
away.

Status:
  enriched              domain and a validated work email
  enrich_no_work_email  domain resolved, no address survived validation
  pending               Clay never returned for this row

A row Clay never reached stays pending rather than being called a resolution
failure. Marking it enrich_no_domain would claim a measurement that was never
taken.

All writes are idempotent PATCHes keyed on cik. Safe to re-run.

Usage:
    py -3 scripts/07_import_clay_results.py
    py -3 scripts/07_import_clay_results.py --dry-run
"""
import os
import sys
import csv
import io
import datetime as dt

import httpx

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CSV = os.path.join(ROOT, "exports", "clay_payload-enriched.csv")
TABLE = "outbound_companies_scored"

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


def g(row, key):
    return (row.get(key) or "").strip()


def split_title(joined, clean_name):
    """'Travis Kalanick, Chief Executive Officer' -> 'Chief Executive Officer'.
    Clay already produced the name half; this recovers the half it discarded."""
    if not joined:
        return None
    if clean_name and joined.lower().startswith(clean_name.lower()):
        rest = joined[len(clean_name):].lstrip(" ,")
        return rest or None
    parts = joined.split(",", 1)
    return parts[1].strip() or None if len(parts) == 2 else None


def main():
    args = sys.argv[1:]
    dry = "--dry-run" in args
    path = DEFAULT_CSV
    if not os.path.exists(path):
        sys.exit("not found: %s" % path)

    env = load_env()
    base = env["SUPABASE_URL"].rstrip("/") + "/rest/v1/" + TABLE
    client = httpx.Client(
        headers={"apikey": env["SUPABASE_SERVICE_ROLE_KEY"],
                 "Authorization": "Bearer " + env["SUPABASE_SERVICE_ROLE_KEY"],
                 "Content-Type": "application/json",
                 "Prefer": "return=representation"},
        timeout=60.0,
    )

    with io.open(path, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    print("read %d rows from %s" % (len(rows), os.path.relpath(path, ROOT)))

    now = dt.datetime.now(dt.timezone.utc).isoformat()
    counts = {"enriched": 0, "enrich_no_work_email": 0, "pending": 0}
    with_copy = 0
    written = 0

    for row in rows:
        cik = g(row, "cik")
        if not cik.isdigit():
            sys.exit("row has no usable cik: %r" % row.get("cik"))

        domain = g(row, "claygent_domain").lower() or None
        email = g(row, "final_email_validated").lower() or None
        body = g(row, "Body") or None
        subject = g(row, "Subject") or None
        name = g(row, "contact_name") or None
        title = split_title(g(row, "contact_name_designation"), name or "")

        if domain and email:
            status = "enriched"
        elif domain:
            status = "enrich_no_work_email"
        else:
            status = "pending"
        counts[status] += 1
        if body:
            with_copy += 1

        patch = {"enrichment_status": status}
        if domain:
            patch["domain"] = domain
            patch["returned_from_clay_at"] = now
        if email:
            patch["work_email"] = email
        if body:
            patch["copy_body"] = body
        if subject:
            patch["subject"] = subject
        if name:
            patch["contact_name"] = name
        if title:
            patch["contact_title"] = title

        if dry:
            continue
        r = client.patch(base, params={"cik": "eq." + cik}, json=patch)
        if r.status_code not in (200, 204):
            sys.exit("PATCH cik=%s -> %s\n%s" % (cik, r.status_code, r.text[:400]))
        got = r.json() if r.text.strip() else []
        if len(got) != 1:
            sys.exit("cik=%s matched %d rows in %s, expected exactly 1"
                     % (cik, len(got), TABLE))
        written += 1

    print()
    print("VERIFICATION")
    print("  csv rows                      %d" % len(rows))
    print("  rows patched                  %d%s" % (written, "  (dry run)" if dry else ""))
    print("  enriched                      %d" % counts["enriched"])
    print("  enrich_no_work_email          %d" % counts["enrich_no_work_email"])
    print("  pending, Clay never returned  %d" % counts["pending"])
    print("  of the enriched, with copy    %d" % with_copy)
    if not dry:
        assert written == len(rows), "short write: %d of %d" % (written, len(rows))

    if dry:
        return

    # Read the table back rather than trusting the writes.
    q = client.get(base, params={
        "select": "cik,domain,work_email,copy_body,subject,contact_name,contact_title,enrichment_status",
        "enrichment_status": "eq.enriched"})
    if q.status_code != 200:
        sys.exit("readback failed: %s %s" % (q.status_code, q.text[:300]))
    back = q.json()
    sendable = [x for x in back if x.get("copy_body") and x.get("work_email")]
    print()
    print("  read back as enriched         %d" % len(back))
    print("  with copy and an address      %d" % len(sendable))
    if len(back) != counts["enriched"]:
        sys.exit("table says %d enriched, this run wrote %d" % (len(back), counts["enriched"]))
    print()
    print("  spot check, addresses redacted:")
    for x in sorted(sendable, key=lambda z: z["cik"])[:8]:
        addr = x["work_email"]
        addr = addr.split("@")[0][:2] + "***@" + addr.split("@")[-1]
        print("    cik=%-9s %-24s %-22s %s"
              % (x["cik"], x["domain"][:24], addr, (x["contact_title"] or "-")[:22]))


if __name__ == "__main__":
    main()
