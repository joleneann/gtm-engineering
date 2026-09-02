#!/usr/bin/env python3
"""
Step 6: collapse companies that share a signer, so one person gets one email.

Reads outbound_companies_unscored (for the signer on each filing) and
outbound_companies_scored. Writes signer_list, and marks the collapsed rows on
outbound_companies_scored.

THE RULE
One human signs Form D for many companies, and those companies are one
operation wearing several names. Measured across the 830 scored: Rezwan Manji
signs for 19, Alfonso Cahero 7, Christopher Kane 4, Tadd Miller 4, and those 34
companies name 7 distinct humans between them. Sending per company is 60 emails
to 7 people.

Above THRESHOLD distinct companies, only the highest-scoring company is
contacted. The rest keep their row, are marked dupe_same_signer, and carry
collapsed_into_cik pointing at the one we kept, so a removal can be opened and
checked rather than trusted. The kept row carries also_signed_for, the sibling
company names, so nothing is lost.

Two and three companies are allowed through deliberately. The contacted_emails
check after Clay catches those on better evidence, once an address exists.

signer_list is a TABLE, built the way mill_list is, because a signer who
appears four times this month appears again in March and has to be caught on
the next pull too.

Names are normalised before counting: "Tadd M. Miller" and "Tadd Miller" are
one human filed two ways and would otherwise count as two signers of four
companies each, neither crossing the threshold.

All writes are idempotent. Re-running re-derives the same grouping and re-marks
the same rows. A row that no longer qualifies is returned to pending, so a
changed threshold cannot leave an earlier collapse standing.

Usage:
    python scripts/05_collapse_signers.py
"""
import os
import re
import sys
import time
from collections import defaultdict

import httpx

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BATCH = 500
THRESHOLD = 3          # more than three distinct companies makes the list


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


def upsert(table, rows, on_conflict):
    if not rows:
        return 0
    headers = {"apikey": SB_KEY, "Authorization": "Bearer " + SB_KEY,
               "Content-Type": "application/json",
               "Prefer": "resolution=merge-duplicates,return=minimal"}
    written = 0
    with httpx.Client(timeout=120) as c:
        for i in range(0, len(rows), BATCH):
            chunk = rows[i:i + BATCH]
            r = c.post("%s/rest/v1/%s" % (SB_URL, table),
                       params={"on_conflict": on_conflict}, headers=headers, json=chunk)
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


def patch(table, filters, payload):
    headers = {"apikey": SB_KEY, "Authorization": "Bearer " + SB_KEY,
               "Content-Type": "application/json", "Prefer": "return=minimal"}
    with httpx.Client(timeout=60) as c:
        r = c.patch("%s/rest/v1/%s" % (SB_URL, table), params=filters,
                    headers=headers, json=payload)
        if r.status_code >= 300:
            sys.exit("patch on %s failed: HTTP %s\n%s" % (table, r.status_code, r.text[:400]))


def normalise_signer(s):
    """Lowercase, drop punctuation, drop single-letter middle initials.

    Tadd M. Miller and Tadd Miller both become 'tadd miller'. Without this he
    counts as two signers of four companies each and neither crosses the
    threshold, so the rule would miss him entirely."""
    s = re.sub(r"[.,]", " ", (s or "").lower())
    parts = [p for p in s.split() if p]
    if len(parts) > 2:
        parts = [parts[0]] + [p for p in parts[1:-1] if len(p) > 1] + [parts[-1]]
    return " ".join(parts).strip()


def main():
    t0 = time.time()
    say("Collapse companies that share a signer\n")

    # The registry is closed: no script mints a code at runtime. The constraint
    # on dedupe_status already accepts this value, so without this check a row
    # could carry a code that reason_codes does not contain and the funnel
    # would count something it cannot name.
    codes = {r["code"] for r in get_all("reason_codes", "code")}
    if "dupe_same_signer" not in codes:
        sys.exit("reason_codes has no 'dupe_same_signer'. Apply PART B of "
                 "db/migration_005_signer_and_email_dedupe.sql first.")

    unscored = get_all("outbound_companies_unscored", "cik,name_of_signer,filing_date")
    scored = get_all("outbound_companies_scored",
                     "cik,current_name_candidates,score,dedupe_status,collapsed_into_cik")
    say("read %d filing rows, %d scored companies" % (len(unscored), len(scored)))

    by_cik = {r["cik"]: r for r in scored}
    name = {c: (r["current_name_candidates"] or [""])[0] for c, r in by_cik.items()}
    score = {c: float(r["score"] or 0) for c, r in by_cik.items()}

    groups, raw_names, dates = defaultdict(set), defaultdict(set), defaultdict(list)
    for r in unscored:
        if r["cik"] not in by_cik:
            continue
        key = normalise_signer(r["name_of_signer"])
        if not key:
            continue
        groups[key].add(r["cik"])
        raw_names[key].add((r["name_of_signer"] or "").strip())
        if r["filing_date"]:
            dates[key].append(r["filing_date"])

    say("distinct signers after normalisation: %d" % len(groups))
    over = {k: v for k, v in groups.items() if len(v) > THRESHOLD}
    say("signers covering more than %d companies: %d" % (THRESHOLD, len(over)))

    # ---- signer_list -----------------------------------------------------
    signer_rows = []
    for key, ciks in over.items():
        signer_rows.append({
            "normalised_signer": key,
            "raw_examples": sorted(raw_names[key])[:5],
            "company_count": len(ciks),
            "company_ciks": sorted(ciks),
            "first_seen": min(dates[key]) if dates[key] else None,
            "last_seen": max(dates[key]) if dates[key] else None,
        })
    upsert("signer_list", signer_rows, "normalised_signer")
    say("signer_list: %d rows written" % len(signer_rows))

    # ---- decide the collapse --------------------------------------------
    keep, drop = {}, {}
    for key, ciks in over.items():
        winner = max(ciks, key=lambda c: (score[c], -c))
        keep[winner] = sorted(name[c] for c in ciks if c != winner)
        for c in ciks:
            if c != winner:
                drop[c] = winner

    say("\ncollapsing")
    for key, ciks in sorted(over.items(), key=lambda kv: -len(kv[1])):
        winner = max(ciks, key=lambda c: (score[c], -c))
        say("   %-26s %2d companies -> keep %-32s (%.2f), route out %d"
            % (key[:26], len(ciks), name[winner][:32], score[winner], len(ciks) - 1))

    for cik, siblings in keep.items():
        patch("outbound_companies_scored", {"cik": "eq.%d" % cik},
              {"also_signed_for": siblings, "collapsed_into_cik": None})
    for cik, winner in drop.items():
        patch("outbound_companies_scored", {"cik": "eq.%d" % cik},
              {"dedupe_status": "dupe_same_signer", "collapsed_into_cik": winner})

    released = 0
    for r in scored:
        if r["dedupe_status"] == "dupe_same_signer" and r["cik"] not in drop:
            patch("outbound_companies_scored", {"cik": "eq.%d" % r["cik"]},
                  {"dedupe_status": "pending", "collapsed_into_cik": None})
            released += 1

    # ---- verification ----------------------------------------------------
    say("\n--- verification ---")
    after = get_all("outbound_companies_scored",
                    "cik,dedupe_status,collapsed_into_cik,also_signed_for,score")
    marked = [r for r in after if r["dedupe_status"] == "dupe_same_signer"]
    kept = [r for r in after if r["also_signed_for"]]
    say("companies scored              : %d" % len(after))
    say("marked dupe_same_signer       : %d (expected %d)" % (len(marked), len(drop)))
    say("kept rows carrying siblings   : %d (expected %d)" % (len(kept), len(keep)))
    say("released back to pending      : %d" % released)
    say("companies now going to Clay   : %d" % (len(after) - len(marked)))

    if len(marked) != len(drop) or len(kept) != len(keep):
        sys.exit("the collapse did not land as computed; fix and re-run")

    orphan = [r for r in marked if not r["collapsed_into_cik"]]
    say("marked rows with no pointer   : %d (must be 0)" % len(orphan))
    if orphan:
        sys.exit("a removed row does not say what it was collapsed into")

    winners = {r["cik"] for r in kept}
    bad = [r for r in marked if r["collapsed_into_cik"] not in winners]
    say("pointers to a non-kept row    : %d (must be 0)" % len(bad))
    if bad:
        sys.exit("a removed row points at something that is not the kept row")

    say("\nspot check, the kept rows:")
    for r in sorted(kept, key=lambda r: -float(r["score"] or 0)):
        say("   %-34s score %.2f, also signed for %d others"
            % (name.get(r["cik"], "?")[:34], float(r["score"] or 0), len(r["also_signed_for"])))
        for sib in r["also_signed_for"][:3]:
            say("      %s" % sib[:60])
        if len(r["also_signed_for"]) > 3:
            say("      ... and %d more" % (len(r["also_signed_for"]) - 3))

    say("\nelapsed: %.1f min" % ((time.time() - t0) / 60))
    say("cost: $0")
    say("\nCOMPLETE: %d companies go to Clay, %d held back as the same person."
        % (len(after) - len(marked), len(marked)))


if __name__ == "__main__":
    main()
