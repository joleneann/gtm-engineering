#!/usr/bin/env python3
"""
Step 5: roll up, score, and build the Clay payload.

Reads outbound_companies_unscored (one row per filing), entities_raw,
filing_related_persons, filing_former_names, industry_scores and mill_list.
Writes outbound_companies_scored, one row per company.

  1. Roll up by CIK over a 365-day window anchored on that company's newest
     filing. Identical offerings refiled collapse on offering_fingerprint.
  2. Amounts summed, sold AND remaining, because both are amounts and the merge
     rule takes only non-amount fields from the newest filing. Industry,
     contact, related persons and filing_date come from the newest filing.
  3. Score out of 10, L = log10(501):
       amount    min(5, 5 * log10(1 + sold/100_000) / L)
       remaining max(0, 1 - min(1, log10(1 + remaining/100_000) / L))
       industry  joined from industry_scores
       prior     0 -> 1.00, 1 -> 0.75, 2 -> 0.50, 3-4 -> 0.25, 5+ -> 0.00,
                 measured as total Form D filed minus the filings rolled here
  4. Build the Clay payload. Address and phone candidates are dropped when
     their normalised form is in mill_list, so an agency's details never reach
     Clay as though they were the company's.

contact_name is blanked when the signer is not the company's own officer: the
authorizedRepresentative flag, or agent wording in signatureTitle. A title
naming a real office BEFORE any agent wording keeps its name, which is what
separates "chief executive officer, duly authorized" from "power of attorney
for samuel seeton, president". See the source of truth, changelog 17.

Nothing is sent anywhere. This fills the payload table; Clay is the next step.

All writes are idempotent upserts on cik, and the post-Clay columns (domain,
work_email, copy_body, the two status columns) are not in the payload, so a
re-run after Clay has returned cannot wipe what Clay wrote.

Usage:
    python scripts/04_score.py
"""
import os
import sys
import json
import math
import time
import datetime as dt
import importlib.util
from collections import defaultdict

import httpx

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BATCH = 500
WINDOW_DAYS = 365
L = math.log10(501)

# The normalisers are loaded from step 4 rather than copied, so the mill check
# here cannot silently drift from the rule that built the list.
_spec = importlib.util.spec_from_file_location(
    "mill_norm", os.path.join(ROOT, "scripts", "03_build_mill_list.py"))
_mill = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mill)
normalise_address = _mill.normalise_address
normalise_phone = _mill.normalise_phone

# Agent wording. A signer whose title hits one of these before it names an
# office is filing on the company's behalf, not working there.
AGENT_PHRASES = (
    "attorney", "power of attorney", "in fact", "in-fact",
    "authorized person", "authorised person",
    "authorized representative", "authorised representative",
    "authorized signatory", "authorised signatory",
    "authorized signer", "authorised signer", "authorized signor",
    "authorized individual", "authorised individual",
    "filing agent", "registered agent", "authorized agent",
    "representative",
)
OFFICE_WORDS = (
    "chief executive", "ceo", "chief financial", "cfo", "chief operating",
    "coo", "chief technology", "cto", "president", "chairman", "chairperson",
    "founder", "general counsel", "secretary", "treasurer", "controller",
    "managing member", "managing director", "manager", "director",
    "vice president", "vp", "partner", "principal", "owner", "member",
    "executive officer",
)


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


def table_count(table):
    headers = {"apikey": SB_KEY, "Authorization": "Bearer " + SB_KEY,
               "Prefer": "count=exact", "Range": "0-0"}
    with httpx.Client(timeout=60) as c:
        r = c.get("%s/rest/v1/%s" % (SB_URL, table), params={"select": "*"}, headers=headers)
        return int(r.headers.get("content-range", "0/0").split("/")[-1])


# ------------------------------------------------------------------ scoring
def curve(v):
    """The shared log curve, 0 at nothing and 1 at $50M."""
    return math.log10(1 + (v or 0) / 100_000.0) / L


def score_amount(sold):
    return round(min(5.0, 5.0 * curve(sold)), 2)


def score_remaining(remaining):
    return round(max(0.0, 1.0 - min(1.0, curve(remaining))), 2)


def score_prior(n):
    if n <= 0:
        return 1.00
    if n == 1:
        return 0.75
    if n == 2:
        return 0.50
    if n <= 4:
        return 0.25
    return 0.00


def blank_contact(title, authorized_representative):
    """True when the signer is an agent rather than the company's own officer.

    Whichever wording comes first decides, so a title that names a real office
    up front survives an 'authorized' later in the string, and an attorney
    signing for a named president does not."""
    if authorized_representative:
        return True
    t = (title or "").strip().lower()
    if not t:
        return False
    agent_at = min((t.find(p) for p in AGENT_PHRASES if p in t), default=-1)
    if agent_at < 0:
        return False
    office_at = min((t.find(w) for w in OFFICE_WORDS if w in t), default=-1)
    return office_at < 0 or agent_at < office_at


# ------------------------------------------------------------------ payload
def dedupe_keep_order(values):
    seen, out = set(), []
    for v in values:
        if not v:
            continue
        v = v.strip()
        k = v.lower()
        if not v or k in seen:
            continue
        seen.add(k)
        out.append(v)
    return out


def readable_address(street1, street2, city, state, zipcode):
    parts = [p.strip() for p in (street1, street2, city, state, zipcode) if p and p.strip()]
    return ", ".join(parts) if parts else None


def main():
    t0 = time.time()
    say("Roll up, score, and build the Clay payload\n")

    say("reading")
    unscored = get_all(
        "outbound_companies_unscored",
        "accession_number,cik,company_name,filing_date,date_of_first_sale,"
        "first_sale_yet_to_occur,total_offering_amount,total_amount_sold,total_remaining,"
        "total_number_already_invested,offering_fingerprint,industry_group_type,entity_type,"
        "issuer_street1,issuer_street2,issuer_city,issuer_state_or_country,issuer_zip,"
        "issuer_phone,name_of_signer,signature_title,authorized_representative")
    entities = {e["cik"]: e for e in get_all(
        "entities_raw",
        "cik,entity_name,website,phone,business_street1,business_street2,business_city,"
        "business_state_or_country,business_zip,former_names,total_form_d_count")}
    persons = get_all("filing_related_persons",
                      "accession_number,cik,seq,first_name,middle_name,last_name,relationships")
    former = get_all("filing_former_names", "accession_number,cik,previous_name,source")
    industry = {r["industry_group_type"]: float(r["points"])
                for r in get_all("industry_scores", "industry_group_type,points")}
    mill = get_all("mill_list", "value_type,normalised_value")
    mill_addr = {r["normalised_value"] for r in mill if r["value_type"] == "address"}
    mill_phone = {r["normalised_value"] for r in mill if r["value_type"] == "phone"}

    by_cik = defaultdict(list)
    for r in unscored:
        by_cik[r["cik"]].append(r)
    persons_by_filing = defaultdict(list)
    for p in persons:
        persons_by_filing[(p["accession_number"], p["cik"])].append(p)
    former_by_cik = defaultdict(list)
    for f in former:
        former_by_cik[f["cik"]].append(f["previous_name"])

    say("   %d filing rows across %d companies" % (len(unscored), len(by_cik)))
    say("   industry_scores: %d codes   mill_list: %d address, %d phone"
        % (len(industry), len(mill_addr), len(mill_phone)))

    unmapped = sorted({r["industry_group_type"] for r in unscored
                       if r["industry_group_type"] not in industry})
    if unmapped:
        say("\nUNMAPPED INDUSTRY CODES, not scoring any of them:")
        for u in unmapped:
            say("   %s" % u)
        sys.exit("extend industry_scores deliberately, then re-run")

    say("\nrolling up and scoring")
    rows, collapsed, blanked, out_of_window = [], 0, 0, 0

    for cik, filings in by_cik.items():
        filings.sort(key=lambda r: (r["filing_date"], r["accession_number"]))
        newest = filings[-1]
        window_end = dt.date.fromisoformat(newest["filing_date"])
        window_start = window_end - dt.timedelta(days=WINDOW_DAYS)

        in_window = []
        for f in filings:
            if dt.date.fromisoformat(f["filing_date"]) >= window_start:
                in_window.append(f)
            else:
                out_of_window += 1

        # identical offerings refiled count once; keep the newest of each group
        seen_fp, kept = set(), []
        for f in reversed(in_window):
            if f["offering_fingerprint"] in seen_fp:
                collapsed += 1
                continue
            seen_fp.add(f["offering_fingerprint"])
            kept.append(f)
        kept.reverse()

        sold = sum(float(f["total_amount_sold"] or 0) for f in kept)
        remaining = sum(float(f["total_remaining"] or 0) for f in kept)

        e = entities.get(cik, {})
        prior = max(0, (e.get("total_form_d_count") or 0) - len(kept))

        s_amount = score_amount(sold)
        s_remaining = score_remaining(remaining)
        s_industry = round(industry[newest["industry_group_type"]], 2)
        s_prior = score_prior(prior)
        total = round(s_amount + s_remaining + s_industry + s_prior, 2)

        # ---- Clay payload
        names = dedupe_keep_order([newest["company_name"], e.get("entity_name")])

        former_names = list(former_by_cik.get(cik, []))
        for fn in (e.get("former_names") or []):
            if isinstance(fn, dict) and fn.get("name"):
                former_names.append(fn["name"])
        former_names = dedupe_keep_order(former_names)

        addr_candidates = []
        for parts in ((newest["issuer_street1"], newest["issuer_street2"], newest["issuer_city"],
                       newest["issuer_state_or_country"], newest["issuer_zip"]),
                      (e.get("business_street1"), e.get("business_street2"), e.get("business_city"),
                       e.get("business_state_or_country"), e.get("business_zip"))):
            readable = readable_address(*parts)
            if not readable:
                continue
            if normalise_address(*parts) in mill_addr:
                continue
            addr_candidates.append(readable)
        addr_candidates = dedupe_keep_order(addr_candidates)

        phone_candidates = []
        for raw in (newest["issuer_phone"], e.get("phone")):
            if not raw:
                continue
            if normalise_phone(raw) in mill_phone:
                continue
            phone_candidates.append(raw)
        phone_candidates = dedupe_keep_order(phone_candidates)

        if blank_contact(newest["signature_title"], newest["authorized_representative"]):
            contact_name = None
            blanked += 1
        else:
            title = (newest["signature_title"] or "").strip()
            signer = (newest["name_of_signer"] or "").strip()
            contact_name = ("%s, %s" % (signer, title)).strip(", ") if signer else None

        people = []
        for p in sorted(persons_by_filing.get((newest["accession_number"], cik), []),
                        key=lambda p: p["seq"]):
            name = " ".join(x for x in (p["first_name"], p["middle_name"], p["last_name"]) if x)
            people.append({"name": name.strip(),
                           "relationships": p["relationships"] or []})

        rows.append({
            "cik": cik,
            "current_name_candidates": names,
            "former_name_candidates": former_names or None,
            "address_candidates": addr_candidates or None,
            "phone_candidates": phone_candidates or None,
            "website_from_edgar": e.get("website"),
            "contact_name": contact_name,
            "people": people or None,
            "amount_sold": round(sold, 2),
            "amount_remaining": round(remaining, 2),
            "industry": newest["industry_group_type"],
            "prior_formd_count": prior,
            "filing_date": newest["filing_date"],
            "score": total,
            "score_amount": s_amount,
            "score_remaining": s_remaining,
            "score_industry": s_industry,
            "score_prior": s_prior,
            "rolled_accessions": [f["accession_number"] for f in kept],
            "rolled_filing_count": len(kept),
            "window_start": window_start.isoformat(),
            "window_end": window_end.isoformat(),
        })

    say("   %d company rows built" % len(rows))
    say("   identical offerings collapsed: %d" % collapsed)
    say("   filings outside the %d-day window: %d" % (WINDOW_DAYS, out_of_window))
    say("   contact_name blanked as an agent: %d" % blanked)

    written = upsert("outbound_companies_scored", rows, "cik")
    say("\noutbound_companies_scored +%d rows (upsert)" % written)

    # ---- verification --------------------------------------------------
    say("\n--- verification ---")

    published_amount = [(0, 0.00), (50_000, 0.33), (100_000, 0.56), (250_000, 1.01),
                        (1_000_000, 1.93), (10_000_000, 3.71), (25_000_000, 4.44),
                        (50_000_000, 5.00)]
    published_remaining = [(0, 1.00), (100_000, 0.89), (1_000_000, 0.61),
                           (10_000_000, 0.26), (50_000_000, 0.00)]
    bad = []
    for v, want in published_amount:
        got = score_amount(v)
        if got != want:
            bad.append(("amount", v, want, got))
    for v, want in published_remaining:
        got = score_remaining(v)
        if got != want:
            bad.append(("remaining", v, want, got))
    say("published curve rows reproduced: %d of %d"
        % (len(published_amount) + len(published_remaining) - len(bad),
           len(published_amount) + len(published_remaining)))
    if bad:
        for b in bad:
            say("   MISMATCH %s %s want %.2f got %.2f" % b)
        sys.exit("the curve no longer reproduces the published table")

    say("companies in  : %d" % len(by_cik))
    say("rows written  : %d" % len(rows))
    say("table rows    : %d" % table_count("outbound_companies_scored"))

    over = [r for r in rows if r["score"] is None or r["score"] > 10.00]
    say("scores above 10.00 or null: %d (must be 0)" % len(over))
    if over:
        sys.exit("a score left the 0 to 10 range")

    buckets = defaultdict(int)
    for r in rows:
        buckets[int(r["score"])] += 1
    say("\nscore distribution:")
    for b in sorted(buckets):
        say("   %2d.00 - %2d.99  %4d  %s" % (b, b, buckets[b], "#" * (buckets[b] // 10)))

    say("\ntop 25 by score:")
    for r in sorted(rows, key=lambda r: -r["score"])[:25]:
        say("   %5.2f  %-38s a%.2f r%.2f i%.2f p%.2f  $%-16s %2d filings  %s"
            % (r["score"], (r["current_name_candidates"] or [""])[0][:38],
               r["score_amount"], r["score_remaining"], r["score_industry"], r["score_prior"],
               "{:,.0f}".format(r["amount_sold"]), r["rolled_filing_count"],
               (r["contact_name"] or "no contact")[:34]))

    say("\nlargest rollups, to confirm several filings became one row:")
    for r in sorted(rows, key=lambda r: -r["rolled_filing_count"])[:5]:
        say("   %-38s %2d filings summed to $%s, score %.2f"
            % ((r["current_name_candidates"] or [""])[0][:38], r["rolled_filing_count"],
               "{:,.0f}".format(r["amount_sold"]), r["score"]))

    say("\npayload completeness:")
    for field in ("current_name_candidates", "address_candidates", "phone_candidates",
                  "contact_name", "people", "website_from_edgar", "former_name_candidates"):
        n = sum(1 for r in rows if r[field])
        say("   %-26s %4d of %d rows (%.0f%%)" % (field, n, len(rows), 100.0 * n / len(rows)))

    say("\nelapsed: %.1f min" % ((time.time() - t0) / 60))
    say("cost: $0")
    say("\nCOMPLETE: %d companies scored, nothing sent anywhere." % len(rows))


if __name__ == "__main__":
    main()
