#!/usr/bin/env python3
"""
Step 02: route filings_raw + entities_raw into scope.

Reads filings_raw (every issuer row: both pulled_reason values, daily_index and
rollup_prior, and every co-issuer, since "one company, one row" applies to
every one of them) and entities_raw. Writes the three route-out tables and
outbound_companies_unscored. Each row exits at the first gate it fails, in
this order (source of truth changelog #10: servicability runs ahead of the
industry park, so a parked company is already known serviceable):

  1. Fund gate, per filing: industryGroupType == 'Pooled Investment Fund' OR
     isPooledInvestmentFundType == true -> formd_funds,
     scope_pooled_investment_fund.
  2. Servicability gate, per company, from entities_raw only (a filing address
     is sometimes an agent's, so this never reads filings_raw except as the
     address fallback below): jurisdiction_fail when state_of_incorporation is
     absent from us_jurisdictions; address_fail when the resolved business
     address code is absent from both us_jurisdictions and
     serviceable_countries. The resolved address code is
     business_state_or_country, falling back to this company's own filing's
     issuer_state_or_country when the history carries no business address (168
     of 2,937 companies, source of truth changelog #13). Either failure routes
     every filing this company has to likely_unserviceable_companies, one row
     per cik, reason codes comma-joined when both fire.
  3. Industry-Other gate, per filing: industryGroupType == 'Other' ->
     no_industry_companies, scope_industry_other.
  4. Survivor, per filing -> outbound_companies_unscored.

Self-heals its own input first: 16 CIKs present in filings_raw (all
pulled_reason=rollup_prior) currently have no entities_raw row, an orphaned
gap from an earlier ingest run before the ingest script's faults were fixed.
Fetches their submissions JSON (free, $0, same endpoint 01_ingest_form_d.py
uses) and backfills entities_raw before routing, rather than guessing a
jurisdiction or dropping them from the gate.

All writes are idempotent upserts. Re-running re-derives the same routing
from the same inputs and produces no duplicates.

Usage:
    python scripts/02_route.py
"""
import os
import sys
import json
import time
import hashlib
import urllib.request
import urllib.error

import httpx

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SLEEP = 0.16
BATCH = 500
RETRIES = 3
BACKOFF = 1.0


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
    for k in ("SEC_USER_AGENT", "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"):
        if not env.get(k):
            sys.exit("%s is not set in .env" % k)
    return env


ENV = load_env()
UA = ENV["SEC_USER_AGENT"]
SB_URL = ENV["SUPABASE_URL"].rstrip("/")
SB_KEY = ENV["SUPABASE_SERVICE_ROLE_KEY"]


def say(msg):
    print(msg)
    sys.stdout.flush()


# ------------------------------------------------------------------- fetch
def _attempt(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode("utf-8", "replace"), False
    except urllib.error.HTTPError as e:
        return e.code, "", 500 <= e.code < 600
    except Exception:                                             # noqa: BLE001
        return 0, "", True
    finally:
        time.sleep(SLEEP)


def fetch(url):
    for attempt in range(RETRIES + 1):
        status, text, retryable = _attempt(url)
        if not retryable or attempt == RETRIES:
            return status, text
        time.sleep(BACKOFF * (2 ** attempt))
    return 0, ""


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


# --------------------------------------------------- entities self-heal
def parse_history(cik, body):
    """Same fields 01_ingest_form_d.py writes to entities_raw. Kept in sync by
    hand: both scripts read the same public JSON shape."""
    d = json.loads(body)
    rec = d.get("filings", {}).get("recent", {}) or {}
    forms = rec.get("form", []) or []
    dates = rec.get("filingDate", []) or []
    accs = rec.get("accessionNumber", []) or []

    hist, n_d, n_da = [], 0, 0
    for f, dd, aa in zip(forms, dates, accs):
        if f == "D":
            n_d += 1
            hist.append({"accession": aa, "filing_date": dd, "form": "D"})
        elif f == "D/A":
            n_da += 1
            hist.append({"accession": aa, "filing_date": dd, "form": "D/A"})

    addr = d.get("addresses") or {}
    b = addr.get("business") or {}
    m = addr.get("mailing") or {}

    def s(v):
        v = (v or "")
        return v.strip() or None

    return {
        "cik": cik,
        "entity_name": s(d.get("name")),
        "entity_type": s(d.get("entityType")),
        "ein": s(d.get("ein")),
        "lei": s(d.get("lei")),
        "sic": s(d.get("sic")),
        "sic_description": s(d.get("sicDescription")),
        "category": s(d.get("category")),
        "description": s(d.get("description")),
        "fiscal_year_end": s(d.get("fiscalYearEnd")),
        "owner_org": s(d.get("ownerOrg")),
        "phone": s(d.get("phone")),
        "website": s(d.get("website")),
        "investor_website": s(d.get("investorWebsite")),
        "state_of_incorporation": s(d.get("stateOfIncorporation")),
        "state_of_incorporation_desc": s(d.get("stateOfIncorporationDescription")),

        "business_street1": s(b.get("street1")),
        "business_street2": s(b.get("street2")),
        "business_city": s(b.get("city")),
        "business_state_or_country": s(b.get("stateOrCountry")),
        "business_zip": s(b.get("zipCode")),
        "business_is_foreign": bool(b.get("isForeignLocation")) if b.get("isForeignLocation") is not None else None,
        "business_country": s(b.get("country")),
        "business_country_code": s(b.get("countryCode")),

        "mailing_street1": s(m.get("street1")),
        "mailing_street2": s(m.get("street2")),
        "mailing_city": s(m.get("city")),
        "mailing_state_or_country": s(m.get("stateOrCountry")),
        "mailing_zip": s(m.get("zipCode")),
        "mailing_is_foreign": bool(m.get("isForeignLocation")) if m.get("isForeignLocation") is not None else None,
        "mailing_country": s(m.get("country")),
        "mailing_country_code": s(m.get("countryCode")),

        "tickers": d.get("tickers") or None,
        "exchanges": d.get("exchanges") or None,
        "former_names": d.get("formerNames") or None,

        "form_d_history": hist or None,
        "total_form_d_count": n_d,
        "form_da_count": n_da,
        "all_form_types": sorted(set(forms)) or None,
    }


def heal_missing_entities(filing_ciks, entities_by_cik):
    missing = sorted(filing_ciks - set(entities_by_cik))
    if not missing:
        say("entities_raw self-heal: nothing missing")
        return
    say("entities_raw self-heal: %d cik(s) in filings_raw have no entities_raw row"
        % len(missing))
    healed, failed = [], []
    for cik in missing:
        status, body = fetch("https://data.sec.gov/submissions/CIK%010d.json" % cik)
        if status != 200:
            failed.append((cik, "submissions HTTP %d" % status))
            continue
        try:
            row = parse_history(cik, body)
        except ValueError as e:
            failed.append((cik, "json_parse_failed: %s" % e))
            continue
        healed.append(row)
        entities_by_cik[cik] = row
    if healed:
        upsert("entities_raw", healed, "cik")
    say("   healed %d, failed %d" % (len(healed), len(failed)))
    if failed:
        say("   FAILED: %s" % failed)
        sys.exit("could not backfill entities_raw for %d cik(s); fix and re-run" % len(failed))


# ------------------------------------------------------------------- main
def main():
    t0 = time.time()
    say("Route filings_raw + entities_raw into scope\n")

    say("reading reference tables")
    us_juris = {r["code"] for r in get_all("us_jurisdictions", "code")}
    serviceable = {r["edgar_code"] for r in get_all("serviceable_countries", "edgar_code")}
    if not serviceable:
        sys.exit("serviceable_countries is empty. Run db/seed_serviceable_countries.sql first.")
    if not us_juris:
        sys.exit("us_jurisdictions is empty. Apply db/schema.sql first.")
    say("   us_jurisdictions: %d codes   serviceable_countries: %d codes" % (len(us_juris), len(serviceable)))

    say("\nreading filings_raw and entities_raw")
    filings = get_all(
        "filings_raw",
        "accession_number,cik,entity_name,filing_date,entity_type,"
        "industry_group_type,investment_fund_type,is_40_act,is_pooled_investment_fund_type,"
        "total_offering_amount,total_amount_sold,total_remaining,total_number_already_invested,"
        "date_of_first_sale,first_sale_yet_to_occur,"
        "issuer_street1,issuer_street2,issuer_city,issuer_state_or_country,issuer_zip,issuer_phone,"
        "name_of_signer,signature_title,authorized_representative",
    )
    entities = get_all(
        "entities_raw",
        "cik,state_of_incorporation,business_state_or_country,website,total_form_d_count",
    )
    entities_by_cik = {e["cik"]: e for e in entities}
    say("   filings_raw: %d rows, %d distinct cik" % (len(filings), len({f["cik"] for f in filings})))
    say("   entities_raw: %d rows" % len(entities))

    say("")
    heal_missing_entities({f["cik"] for f in filings}, entities_by_cik)

    # ---- servicability verdict, once per company -------------------------
    say("\ndeciding servicability, per company")
    fallback_addr = {}
    for f in sorted(filings, key=lambda r: r["accession_number"]):
        fallback_addr.setdefault(f["cik"], f["issuer_state_or_country"])

    verdict = {}   # cik -> row for likely_unserviceable_companies
    no_history_addr_used = 0
    for cik, e in entities_by_cik.items():
        jurisdiction_fail = e["state_of_incorporation"] not in us_juris
        addr_code = e["business_state_or_country"]
        if addr_code is None:
            addr_code = fallback_addr.get(cik)
            if addr_code is not None:
                no_history_addr_used += 1
        address_fail = addr_code is None or (addr_code not in us_juris and addr_code not in serviceable)
        if not (jurisdiction_fail or address_fail):
            continue
        codes = []
        if jurisdiction_fail:
            codes.append("scope_non_us_incorporation")
        if address_fail:
            codes.append("scope_unsupported_country")
        verdict[cik] = {
            "cik": cik,
            "company_name": None,  # filled below, once every filing's been scanned for a name
            "jurisdiction_of_inc": e["state_of_incorporation"],
            "business_state_or_country": addr_code,
            "business_country_code": e.get("business_country_code"),
            "jurisdiction_fail": jurisdiction_fail,
            "address_fail": address_fail,
            "reason_code": ",".join(codes),
        }
    say("   %d companies fail servicability (%d used the filing as address fallback)"
        % (len(verdict), no_history_addr_used))

    # company_name for the verdict rows: first filing's issuer/entity name
    name_by_cik = {}
    for f in filings:
        name_by_cik.setdefault(f["cik"], f["entity_name"])
    for cik, row in verdict.items():
        row["company_name"] = name_by_cik.get(cik)

    # ---- route every filing row ------------------------------------------
    say("\nrouting %d filing rows" % len(filings))
    funds, unserviceable_filing_count, parked, survivors = [], 0, [], []

    for f in filings:
        cik = f["cik"]
        is_fund_industry = f["industry_group_type"] == "Pooled Investment Fund"
        is_fund_tick = bool(f["is_pooled_investment_fund_type"])
        if is_fund_industry or is_fund_tick:
            detected_by = "both" if (is_fund_industry and is_fund_tick) else (
                "industry_group" if is_fund_industry else "securities_tick")
            funds.append({
                "accession_number": f["accession_number"],
                "cik": cik,
                "company_name": f["entity_name"],
                "filing_date": f["filing_date"],
                "industry_group_type": f["industry_group_type"],
                "investment_fund_type": f["investment_fund_type"],
                "is_40_act": f["is_40_act"],
                "is_pooled_tick": f["is_pooled_investment_fund_type"],
                "detected_by": detected_by,
                "total_amount_sold": f["total_amount_sold"],
                "reason_code": "scope_pooled_investment_fund",
            })
            continue

        if cik in verdict:
            unserviceable_filing_count += 1
            continue

        e = entities_by_cik[cik]
        if f["industry_group_type"] == "Other":
            prior = e["total_form_d_count"] - 1
            parked.append({
                "accession_number": f["accession_number"],
                "cik": cik,
                "company_name": f["entity_name"],
                "filing_date": f["filing_date"],
                "industry_group_type": f["industry_group_type"],
                "total_amount_sold": f["total_amount_sold"],
                "total_remaining": f["total_remaining"],
                "date_of_first_sale": f["date_of_first_sale"],
                "first_sale_yet_to_occur": f["first_sale_yet_to_occur"],
                "prior_formd_count": max(0, prior),
                "issuer_phone": f["issuer_phone"],
                "issuer_street1": f["issuer_street1"],
                "issuer_city": f["issuer_city"],
                "issuer_state_or_country": f["issuer_state_or_country"],
                "issuer_zip": f["issuer_zip"],
                "website_from_edgar": e["website"],
                "reason_code": "scope_industry_other",
            })
            continue

        fp_src = "|".join(str(x) for x in (
            f["total_offering_amount"], f["total_amount_sold"],
            f["date_of_first_sale"], f["total_number_already_invested"]))
        survivors.append({
            "accession_number": f["accession_number"],
            "cik": cik,
            "company_name": f["entity_name"],
            "filing_date": f["filing_date"],
            "date_of_first_sale": f["date_of_first_sale"],
            "first_sale_yet_to_occur": f["first_sale_yet_to_occur"],
            "total_offering_amount": f["total_offering_amount"],
            "total_amount_sold": f["total_amount_sold"],
            "total_remaining": f["total_remaining"],
            "total_number_already_invested": f["total_number_already_invested"],
            "offering_fingerprint": hashlib.sha256(fp_src.encode()).hexdigest(),
            "industry_group_type": f["industry_group_type"],
            "entity_type": f["entity_type"],
            "issuer_street1": f["issuer_street1"],
            "issuer_street2": f["issuer_street2"],
            "issuer_city": f["issuer_city"],
            "issuer_state_or_country": f["issuer_state_or_country"],
            "issuer_zip": f["issuer_zip"],
            "issuer_phone": f["issuer_phone"],
            "name_of_signer": f["name_of_signer"],
            "signature_title": f["signature_title"],
            "authorized_representative": f["authorized_representative"],
        })

    # ---- write -------------------------------------------------------------
    say("\nwriting")
    w_funds = upsert("formd_funds", funds, "accession_number,cik")
    w_unserv = upsert("likely_unserviceable_companies", list(verdict.values()), "cik")
    w_parked = upsert("no_industry_companies", parked, "accession_number,cik")
    w_surv = upsert("outbound_companies_unscored", survivors, "accession_number,cik")
    say("   formd_funds                    +%d rows (upsert)" % w_funds)
    say("   likely_unserviceable_companies +%d rows (upsert, one per company)" % w_unserv)
    say("   no_industry_companies          +%d rows (upsert)" % w_parked)
    say("   outbound_companies_unscored    +%d rows (upsert)" % w_surv)

    # ---- verification -------------------------------------------------------
    say("\n--- verification ---")
    total = len(filings)
    routed = len(funds) + unserviceable_filing_count + len(parked) + len(survivors)
    say("filing rows in                : %d" % total)
    say("  -> formd_funds               : %d" % len(funds))
    say("       securities_tick-only    : %d" % sum(1 for r in funds if r["detected_by"] == "securities_tick"))
    say("       industry_group-only     : %d" % sum(1 for r in funds if r["detected_by"] == "industry_group"))
    say("       both                    : %d" % sum(1 for r in funds if r["detected_by"] == "both"))
    say("  -> likely_unserviceable      : %d filing rows (%d distinct companies)"
        % (unserviceable_filing_count, len(verdict)))
    say("       jurisdiction_fail only  : %d" % sum(1 for r in verdict.values() if r["jurisdiction_fail"] and not r["address_fail"]))
    say("       address_fail only       : %d" % sum(1 for r in verdict.values() if r["address_fail"] and not r["jurisdiction_fail"]))
    say("       both                    : %d" % sum(1 for r in verdict.values() if r["jurisdiction_fail"] and r["address_fail"]))
    say("  -> no_industry_companies     : %d" % len(parked))
    say("  -> outbound_companies_unscored: %d" % len(survivors))
    say("routed total                  : %d" % routed)

    for t in ("formd_funds", "likely_unserviceable_companies", "no_industry_companies",
              "outbound_companies_unscored"):
        say("table %-30s %d rows" % (t, table_count(t)))

    say("\nspot check, first 10 per reason code:")
    for label, rows in (("scope_pooled_investment_fund", funds),
                         ("likely_unserviceable_companies", list(verdict.values())),
                         ("scope_industry_other", parked)):
        say("  %s:" % label)
        for r in rows[:10]:
            say("    cik=%s  %s" % (r["cik"], r["company_name"]))

    say("\nelapsed: %.1f min" % ((time.time() - t0) / 60))
    say("cost: $0")

    if routed != total:
        sys.exit("\nROUTING INCOMPLETE: %d filing rows in, %d routed. A row was lost or "
                  "double-counted; fix and re-run." % (total, routed))
    say("\nCOMPLETE: every one of %d filing rows accounted for exactly once." % total)


if __name__ == "__main__":
    main()
