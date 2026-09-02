#!/usr/bin/env python3
"""
Step 4: build the mill list.

Reads every issuer address and phone number in filings_raw (every filing,
regardless of what 02_route.py did with it: a filing agent files for funds
too). Normalises each, counts how many filing rows and how many distinct
CIKs share the normalised value, and writes to mill_list every value shared
by MORE THAN THREE DISTINCT COMPANIES.

The membership test is distinct companies, never raw occurrences, because the
two counts mean opposite things. An address recurring 74 times for a single
CIK is that company's own head office, and an occurrence test put 101 such
values on a 213-row list, which would have stripped both address and phone
from 56 of the 830 surviving companies. See the source of truth, changelog 15.

Runs before the Clay payload is built (step 5), because the payload dedupes
candidate addresses and phones against this list rather than sending an
agency's address as if it were the company's own.

Address normalisation: uppercase, punctuation stripped, common street-type
words expanded (ST -> STREET, AVE -> AVENUE, ...), street1/street2/city/
state-or-country-code/zip joined with a single space, zip trimmed to its
first 5 digits so a ZIP+4 and a ZIP5 for the same address collapse together.

Phone normalisation: every non-digit character stripped, then a leading
country-code 1 dropped, so "+1 (555) 123-4567" and "555-123-4567" collapse to
the same 10 digits.

All writes are idempotent upserts. Re-running re-derives the same counts from
the same filings_raw and produces no duplicates.

Usage:
    python scripts/03_build_mill_list.py
"""
import os
import re
import sys
import time

import httpx

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BATCH = 500
THRESHOLD = 3          # more than three DISTINCT COMPANIES makes the list
MAX_EXAMPLES = 5

STREET_WORDS = {
    "ST": "STREET", "AVE": "AVENUE", "AV": "AVENUE", "BLVD": "BOULEVARD",
    "DR": "DRIVE", "RD": "ROAD", "LN": "LANE", "CT": "COURT", "CIR": "CIRCLE",
    "PL": "PLACE", "SQ": "SQUARE", "STE": "SUITE", "FL": "FLOOR",
    "APT": "APARTMENT", "HWY": "HIGHWAY", "PKWY": "PARKWAY", "TER": "TERRACE",
    "TRL": "TRAIL", "PLZ": "PLAZA", "BLDG": "BUILDING",
}


# ------------------------------------------------------------------ config
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


ENV = load_env()
SB_URL = ENV["SUPABASE_URL"].rstrip("/")
SB_KEY = ENV["SUPABASE_SERVICE_ROLE_KEY"]


def say(msg):
    print(msg)
    sys.stdout.flush()


# ---------------------------------------------------------------- supabase
def upsert(table, rows, on_conflict):
    if not rows:
        return 0
    headers = {
        "apikey": SB_KEY,
        "Authorization": "Bearer " + SB_KEY,
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }
    written = 0
    with httpx.Client(timeout=120) as c:
        for i in range(0, len(rows), BATCH):
            chunk = rows[i:i + BATCH]
            r = c.post("%s/rest/v1/%s" % (SB_URL, table),
                       params={"on_conflict": on_conflict},
                       headers=headers, json=chunk)
            if r.status_code >= 300:
                sys.exit("upsert into %s failed: HTTP %s\n%s"
                         % (table, r.status_code, r.text[:600]))
            written += len(chunk)
    return written


def get_all(table, select, page=1000):
    headers = {"apikey": SB_KEY, "Authorization": "Bearer " + SB_KEY}
    out, off = [], 0
    with httpx.Client(timeout=120) as c:
        while True:
            r = c.get("%s/rest/v1/%s" % (SB_URL, table),
                      params={"select": select, "limit": str(page), "offset": str(off)},
                      headers=headers)
            if r.status_code >= 300:
                sys.exit("could not read %s: HTTP %s\n%s" % (table, r.status_code, r.text[:300]))
            rows = r.json()
            out.extend(rows)
            if len(rows) < page:
                return out
            off += page


def delete_row(table, filters):
    headers = {"apikey": SB_KEY, "Authorization": "Bearer " + SB_KEY,
               "Prefer": "return=minimal"}
    with httpx.Client(timeout=60) as c:
        r = c.delete("%s/rest/v1/%s" % (SB_URL, table), params=filters, headers=headers)
        if r.status_code >= 300:
            sys.exit("delete from %s failed: HTTP %s\n%s" % (table, r.status_code, r.text[:400]))


def table_count(table):
    headers = {"apikey": SB_KEY, "Authorization": "Bearer " + SB_KEY,
               "Prefer": "count=exact", "Range": "0-0"}
    with httpx.Client(timeout=60) as c:
        r = c.get("%s/rest/v1/%s" % (SB_URL, table), params={"select": "*"}, headers=headers)
        return int(r.headers.get("content-range", "0/0").split("/")[-1])


# --------------------------------------------------------------- normalise
def normalise_address(street1, street2, city, state_or_country, zip_code):
    if not street1 and not city:
        return None
    parts = []
    for part in (street1, street2, city, state_or_country):
        if not part:
            continue
        p = re.sub(r"[.,#]", " ", part.upper())
        p = re.sub(r"\s+", " ", p).strip()
        tokens = [STREET_WORDS.get(tok, tok) for tok in p.split(" ")]
        parts.append(" ".join(tokens))
    if zip_code:
        z = re.sub(r"\D", "", zip_code)[:5]
        if z:
            parts.append(z)
    value = " ".join(parts).strip()
    return value or None


def normalise_phone(phone):
    if not phone:
        return None
    digits = re.sub(r"\D", "", phone)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return digits or None


# ------------------------------------------------------------------- main
def main():
    t0 = time.time()
    say("Build the mill list\n")

    say("reading filings_raw")
    filings = get_all(
        "filings_raw",
        "cik,filing_date,issuer_street1,issuer_street2,issuer_city,"
        "issuer_state_or_country,issuer_zip,issuer_phone",
    )
    say("   %d rows" % len(filings))

    # value_type -> normalised_value -> {count, raw: set(), ciks: set(), dates: [...]}
    agg = {"address": {}, "phone": {}}

    for f in filings:
        addr = normalise_address(f["issuer_street1"], f["issuer_street2"],
                                  f["issuer_city"], f["issuer_state_or_country"],
                                  f["issuer_zip"])
        if addr:
            raw = ", ".join(x for x in (f["issuer_street1"], f["issuer_street2"],
                                         f["issuer_city"], f["issuer_state_or_country"],
                                         f["issuer_zip"]) if x)
            bucket = agg["address"].setdefault(
                addr, {"count": 0, "raw": set(), "ciks": set(), "dates": []})
            bucket["count"] += 1
            bucket["raw"].add(raw)
            bucket["ciks"].add(f["cik"])
            if f["filing_date"]:
                bucket["dates"].append(f["filing_date"])

        phone = normalise_phone(f["issuer_phone"])
        if phone:
            bucket = agg["phone"].setdefault(
                phone, {"count": 0, "raw": set(), "ciks": set(), "dates": []})
            bucket["count"] += 1
            bucket["raw"].add(f["issuer_phone"])
            bucket["ciks"].add(f["cik"])
            if f["filing_date"]:
                bucket["dates"].append(f["filing_date"])

    say("   %d distinct normalised addresses, %d distinct normalised phones"
        % (len(agg["address"]), len(agg["phone"])))

    rows = []
    for value_type, buckets in agg.items():
        for normalised_value, b in buckets.items():
            if len(b["ciks"]) <= THRESHOLD:
                continue
            rows.append({
                "value_type": value_type,
                "normalised_value": normalised_value,
                "raw_examples": sorted(b["raw"])[:MAX_EXAMPLES],
                "occurrence_count": b["count"],
                "distinct_cik_count": len(b["ciks"]),
                "first_seen": min(b["dates"]) if b["dates"] else None,
                "last_seen": max(b["dates"]) if b["dates"] else None,
            })

    say("\n%d values are shared by more than %d distinct companies and make the list "
        "(%d address, %d phone)"
        % (len(rows), THRESHOLD,
           sum(1 for r in rows if r["value_type"] == "address"),
           sum(1 for r in rows if r["value_type"] == "phone")))

    # Remove anything already in the table that no longer qualifies, so the list
    # is what the current filings_raw says it is rather than the union of every
    # rule this script has ever run under. Without this a re-run can only add.
    want = {(r["value_type"], r["normalised_value"]) for r in rows}
    held = {(r["value_type"], r["normalised_value"])
            for r in get_all("mill_list", "value_type,normalised_value")}
    stale = sorted(held - want)
    for value_type, normalised_value in stale:
        delete_row("mill_list", {"value_type": "eq.%s" % value_type,
                                 "normalised_value": "eq.%s" % normalised_value})
    say("mill_list -%d rows that no longer qualify" % len(stale))

    written = upsert("mill_list", rows, "value_type,normalised_value")
    say("mill_list +%d rows (upsert)" % written)
    say("table mill_list: %d rows total" % table_count("mill_list"))

    say("\n--- verification: top 20 by occurrence_count ---")
    for r in sorted(rows, key=lambda r: -r["occurrence_count"])[:20]:
        say("   %-8s %4dx  %3d distinct cik  %-60s %s"
            % (r["value_type"], r["occurrence_count"], r["distinct_cik_count"],
               r["normalised_value"][:60], r["raw_examples"][:2]))

    solo = [r for r in rows if r["distinct_cik_count"] <= THRESHOLD]
    say("\nrows written that only %d or fewer companies share: %d (must be 0)"
        % (THRESHOLD, len(solo)))
    if solo:
        sys.exit("a value used by %d or fewer companies reached mill_list; fix and re-run" % THRESHOLD)

    say("\nelapsed: %.1f min" % ((time.time() - t0) / 60))
    say("cost: $0")


if __name__ == "__main__":
    main()
