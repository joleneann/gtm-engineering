#!/usr/bin/env python3
"""
Step 01: ingest SEC Form D into filings_raw, its two child tables, and entities_raw.

Three public SEC endpoints, no key, no scraping, $0:

  1. the day's filing index
     https://www.sec.gov/Archives/edgar/daily-index/{YYYY}/QTR{n}/form.{YYYYMMDD}.idx
     Plain text, form type is the first column, so D/A is skipped without
     downloading anything.

  2. the filing
     https://www.sec.gov/Archives/edgar/data/{CIK}/{accession-no-dashes}/primary_doc.xml

  3. the company's whole filing history
     https://data.sec.gov/submissions/CIK{cik:010d}.json
     CIK MUST be zero-padded to ten digits or the endpoint 404s.

Plus a fourth pass: prior Form D filed within 365 days of a company's newest
filing, which the 12-month rollup in step 5 needs. The accessions come free
from the submissions JSON, so only the ones actually inside the window are
fetched. Measured at 0.28 extra fetches per company.

Every named issuer on a filing gets its own row. Where several CIKs share a
raise, that raise is counted in full for every CIK: the offering amounts are
reported once for the whole filing and are not split. See the source of truth.

Rate limit: SEC allows 10 req/sec and requires a contact User-Agent. This
sleeps 0.16s between requests (~6/sec), pacing under the limit rather than
retrying into it.

All writes are idempotent upserts. Re-running produces no duplicates.
The run asserts that filings written equals filings in the index and exits
non-zero if it is short. No partial state is accepted: fix and re-run.

Usage:
    python scripts/01_ingest_form_d.py 2026-08-05 2026-09-01
    python scripts/01_ingest_form_d.py 2026-08-05 2026-09-01 --limit 20
    python scripts/01_ingest_form_d.py --no-priors 2026-09-01 2026-09-01
"""
import os
import sys
import json
import time
import hashlib
import datetime as dt
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET

import httpx

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SLEEP = 0.16          # under SEC's 10 req/sec: paced, not retried into
BATCH = 500
ROLLUP_DAYS = 365
RETRIES = 3           # transient failures only: timeout, reset, 5xx
BACKOFF = 1.0         # seconds, doubled each attempt


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

STATS = {"req": 0, "http_err": {}, "retried": 0, "gave_up": 0}


# ------------------------------------------------------------------- fetch
def _attempt(url, encoding):
    """One request. (status, text, retryable). status 0 means the connection
    never completed."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    STATS["req"] += 1
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode(encoding, "replace"), False
    except urllib.error.HTTPError as e:
        STATS["http_err"][e.code] = STATS["http_err"].get(e.code, 0) + 1
        # 5xx is the server temporarily unable. 429 is a rate limit, which the
        # contract says is paced around and never retried into: a 429 means the
        # pacing above is wrong and retrying would make it worse. 403 and 404
        # are answers, not failures.
        return e.code, "", 500 <= e.code < 600
    except Exception as e:                                      # noqa: BLE001
        # timeout, connection reset, DNS: the request never got an answer
        k = type(e).__name__
        STATS["http_err"][k] = STATS["http_err"].get(k, 0) + 1
        return 0, "", True
    finally:
        time.sleep(SLEEP)


def fetch(url, encoding="utf-8"):
    """(status, text). Paced under the SEC limit, and transient failures are
    retried with backoff.

    The distinction matters and the first full run proved it: 14 documents were
    lost to one-off timeouts, resets and 503s because there was no retry at all.
    A rate limit is paced around; a transient failure is retried.
    """
    for attempt in range(RETRIES + 1):
        status, text, retryable = _attempt(url, encoding)
        if not retryable or attempt == RETRIES:
            if retryable:
                STATS["gave_up"] += 1
            return status, text
        STATS["retried"] += 1
        time.sleep(BACKOFF * (2 ** attempt))
    return 0, ""


# ---------------------------------------------------------------- supabase
def upsert(table, rows, on_conflict):
    """Batched idempotent upsert through PostgREST."""
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


def existing_accessions():
    """Every (accession, cik) already in filings_raw, paged.

    A re-run fetches only what is missing. Transient SEC failures (503, reset,
    timeout) cost a handful of filings out of thousands, and refetching the
    whole window to recover fourteen documents is 85 minutes of waste.
    """
    headers = {"apikey": SB_KEY, "Authorization": "Bearer " + SB_KEY}
    out, offset, page = set(), 0, 1000
    with httpx.Client(timeout=120) as c:
        while True:
            r = c.get("%s/rest/v1/filings_raw" % SB_URL,
                      params={"select": "accession_number,cik", "limit": str(page),
                              "offset": str(offset)}, headers=headers)
            if r.status_code >= 300:
                sys.exit("could not read filings_raw: HTTP %s\n%s" % (r.status_code, r.text[:300]))
            rows = r.json()
            for x in rows:
                out.add((x["accession_number"], x["cik"]))
            if len(rows) < page:
                return out
            offset += page


def table_count(table):
    headers = {"apikey": SB_KEY, "Authorization": "Bearer " + SB_KEY,
               "Prefer": "count=exact", "Range": "0-0"}
    with httpx.Client(timeout=60) as c:
        r = c.get("%s/rest/v1/%s" % (SB_URL, table),
                  params={"select": "*"}, headers=headers)
        return int(r.headers.get("content-range", "0/0").split("/")[-1])


# -------------------------------------------------------------- xml coerce
def strip_ns(tag):
    return tag.split("}", 1)[-1] if "}" in tag else tag


def txt(node, path, default=None):
    """First text value at a slash path below node, or default."""
    cur = [node]
    for part in path.split("/"):
        nxt = []
        for n in cur:
            nxt.extend([c for c in n if strip_ns(c.tag) == part])
        cur = nxt
        if not cur:
            return default
    v = (cur[0].text or "").strip()
    return v if v else default


def all_txt(node, path):
    """Every text value at a slash path below node."""
    cur = [node]
    for part in path.split("/"):
        nxt = []
        for n in cur:
            nxt.extend([c for c in n if strip_ns(c.tag) == part])
        cur = nxt
    return [(n.text or "").strip() for n in cur if (n.text or "").strip()]


def children(node, path):
    cur = [node]
    for part in path.split("/"):
        nxt = []
        for n in cur:
            nxt.extend([c for c in n if strip_ns(c.tag) == part])
        cur = nxt
    return cur


def as_bool(v):
    if v is None:
        return None
    return v.strip().lower() in ("true", "1", "y", "yes")


def as_num(v):
    if v is None:
        return None
    try:
        return float(str(v).replace(",", "").strip())
    except ValueError:
        return None


def as_int(v):
    n = as_num(v)
    return int(n) if n is not None else None


def as_date(v):
    if not v:
        return None
    v = v.strip()[:10]
    try:
        dt.date.fromisoformat(v)
        return v
    except ValueError:
        return None


# ------------------------------------------------------------- 1. the index
def read_index(day):
    """[(company_name, cik, archive_path)] for form type D only.
    Returns None when the day publishes no index: a weekend or market holiday
    is a no-op, not a failure."""
    qtr = (day.month - 1) // 3 + 1
    url = ("https://www.sec.gov/Archives/edgar/daily-index/%d/QTR%d/form.%s.idx"
           % (day.year, qtr, day.strftime("%Y%m%d")))
    status, text = fetch(url, "latin-1")
    if status != 200:
        return None
    rows = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 4 or not parts[-1].startswith("edgar/data/"):
            continue
        if parts[0] == "D":
            rows.append((" ".join(parts[1:-3]), int(parts[-3]), parts[-1]))
    return rows


# ------------------------------------------------------- 2. parse a filing
def issuer_columns(iss):
    """The shared issuer block: identical shape for primaryIssuer and for each
    entry in issuerList, which is why co-issuers reuse these columns."""
    return {
        "entity_name":                   txt(iss, "entityName"),
        "entity_type":                   txt(iss, "entityType"),
        "entity_type_other_desc":        txt(iss, "entityTypeOtherDesc"),
        "jurisdiction_of_inc":           txt(iss, "jurisdictionOfInc"),
        "issuer_phone":                  txt(iss, "issuerPhoneNumber"),
        "year_of_inc_value":             txt(iss, "yearOfInc/value"),
        "year_of_inc_within_five_years": as_bool(txt(iss, "yearOfInc/withinFiveYears")),
        "year_of_inc_over_five_years":   as_bool(txt(iss, "yearOfInc/overFiveYears")),
        "year_of_inc_yet_to_be_formed":  as_bool(txt(iss, "yearOfInc/yetToBeFormed")),
        "issuer_street1":                txt(iss, "issuerAddress/street1"),
        "issuer_street2":                txt(iss, "issuerAddress/street2"),
        "issuer_city":                   txt(iss, "issuerAddress/city"),
        "issuer_state_or_country":       txt(iss, "issuerAddress/stateOrCountry"),
        "issuer_state_or_country_desc":  txt(iss, "issuerAddress/stateOrCountryDescription"),
        "issuer_zip":                    txt(iss, "issuerAddress/zipCode"),
    }


def offering_columns(root):
    od = children(root, "offeringData")
    od = od[0] if od else ET.Element("empty")
    sc = []
    for rec in children(od, "salesCompensationList/recipient"):
        sc.append({
            "recipient_name":        txt(rec, "recipientName"),
            "recipient_crd":         txt(rec, "recipientCRDNumber"),
            "associated_bd_name":    txt(rec, "associatedBDName"),
            "associated_bd_crd":     txt(rec, "associatedBDCRDNumber"),
            "foreign_solicitation":  as_bool(txt(rec, "foreignSolicitation")),
            "street1":               txt(rec, "recipientAddress/street1"),
            "city":                  txt(rec, "recipientAddress/city"),
            "state_or_country":      txt(rec, "recipientAddress/stateOrCountry"),
            "zip":                   txt(rec, "recipientAddress/zipCode"),
            "states_of_solicitation": all_txt(rec, "statesOfSolicitationList/value"),
        })
    return {
        "schema_version":   txt(root, "schemaVersion"),
        "submission_type":  txt(root, "submissionType"),
        "test_or_live":     txt(root, "testOrLive"),
        "is_amendment":     as_bool(txt(od, "typeOfFiling/newOrAmendment/isAmendment")),

        "industry_group_type":  txt(od, "industryGroup/industryGroupType"),
        "investment_fund_type": txt(od, "industryGroup/investmentFundInfo/investmentFundType"),
        "is_40_act":            as_bool(txt(od, "industryGroup/investmentFundInfo/is40Act")),
        "revenue_range":        txt(od, "issuerSize/revenueRange"),
        "aggregate_net_asset_value_range": txt(od, "issuerSize/aggregateNetAssetValueRange"),
        "date_of_first_sale":   as_date(txt(od, "typeOfFiling/dateOfFirstSale/value")),
        "first_sale_yet_to_occur": as_bool(txt(od, "typeOfFiling/dateOfFirstSale/yetToOccur")),
        "duration_more_than_one_year": as_bool(txt(od, "durationOfOffering/moreThanOneYear")),
        "minimum_investment_accepted": as_num(txt(od, "minimumInvestmentAccepted")),
        "total_offering_amount": as_num(txt(od, "offeringSalesAmounts/totalOfferingAmount")),
        "total_amount_sold":     as_num(txt(od, "offeringSalesAmounts/totalAmountSold")),
        "total_remaining":       as_num(txt(od, "offeringSalesAmounts/totalRemaining")),
        "offering_amounts_clarification": txt(od, "offeringSalesAmounts/clarificationOfResponse"),
        "has_non_accredited_investors": as_bool(txt(od, "investors/hasNonAccreditedInvestors")),
        "number_non_accredited_investors": as_int(txt(od, "investors/numberNonAccreditedInvestors")),
        "total_number_already_invested": as_int(txt(od, "investors/totalNumberAlreadyInvested")),

        "is_equity_type":       as_bool(txt(od, "typesOfSecuritiesOffered/isEquityType")),
        "is_debt_type":         as_bool(txt(od, "typesOfSecuritiesOffered/isDebtType")),
        "is_option_to_acquire_type": as_bool(txt(od, "typesOfSecuritiesOffered/isOptionToAcquireType")),
        "is_security_to_be_acquired_type": as_bool(txt(od, "typesOfSecuritiesOffered/isSecurityToBeAcquiredType")),
        "is_pooled_investment_fund_type": as_bool(txt(od, "typesOfSecuritiesOffered/isPooledInvestmentFundType")),
        "is_tenant_in_common_type": as_bool(txt(od, "typesOfSecuritiesOffered/isTenantInCommonType")),
        "is_mineral_property_type": as_bool(txt(od, "typesOfSecuritiesOffered/isMineralPropertyType")),
        "is_other_type":        as_bool(txt(od, "typesOfSecuritiesOffered/isOtherType")),
        "description_of_other_type": txt(od, "typesOfSecuritiesOffered/descriptionOfOtherType"),

        "federal_exemptions":  all_txt(od, "federalExemptionsExclusions/item") or None,

        "is_business_combination_transaction":
            as_bool(txt(od, "businessCombinationTransaction/isBusinessCombinationTransaction")),
        "business_combination_clarification":
            txt(od, "businessCombinationTransaction/clarificationOfResponse"),

        "sales_commissions_amount": as_num(txt(od, "salesCommissionsFindersFees/salesCommissions/dollarAmount")),
        "sales_commissions_is_estimate": as_bool(txt(od, "salesCommissionsFindersFees/salesCommissions/isEstimate")),
        "finders_fees_amount":     as_num(txt(od, "salesCommissionsFindersFees/findersFees/dollarAmount")),
        "finders_fees_is_estimate": as_bool(txt(od, "salesCommissionsFindersFees/findersFees/isEstimate")),
        "commissions_clarification": txt(od, "salesCommissionsFindersFees/clarificationOfResponse"),
        "gross_proceeds_used_amount": as_num(txt(od, "useOfProceeds/grossProceedsUsed/dollarAmount")),
        "gross_proceeds_used_is_estimate": as_bool(txt(od, "useOfProceeds/grossProceedsUsed/isEstimate")),
        "use_of_proceeds_clarification": txt(od, "useOfProceeds/clarificationOfResponse"),

        "signature_issuer_name":  txt(od, "signatureBlock/signature/issuerName"),
        "name_of_signer":         txt(od, "signatureBlock/signature/nameOfSigner"),
        "signature_name":         txt(od, "signatureBlock/signature/signatureName"),
        "signature_title":        txt(od, "signatureBlock/signature/signatureTitle"),
        "signature_date":         as_date(txt(od, "signatureBlock/signature/signatureDate")),
        "authorized_representative": as_bool(txt(od, "signatureBlock/authorizedRepresentative")),

        "sales_compensation":     sc or None,
    }


def parse_filing(xml, accession, filing_date, index_name, archive_path, pulled_reason):
    """-> (filing rows, related-person rows, former-name rows).

    One row per named issuer. The offering block is shared, so every co-issuer
    row carries the full amount: several CIKs sharing a raise each count it in
    full, by decision.
    """
    root = ET.fromstring(xml)
    offering = offering_columns(root)

    issuers = []
    prim = children(root, "primaryIssuer")
    if prim:
        issuers.append((prim[0], True))
    for iss in children(root, "issuerList/issuer"):
        issuers.append((iss, False))

    filings, persons, names = [], [], []
    seen_ciks = set()

    for iss, is_primary in issuers:
        cik = as_int(txt(iss, "cik"))
        if cik is None or cik in seen_ciks:
            continue
        seen_ciks.add(cik)

        row = {
            "accession_number": accession,
            "cik": cik,
            "is_primary_issuer": is_primary,
            "form_type": "D",
            "filing_date": filing_date,
            "company_name_index": index_name if is_primary else txt(iss, "entityName"),
            "archive_path": archive_path,
            "pulled_reason": pulled_reason,
        }
        row.update(issuer_columns(iss))
        row.update(offering)
        filings.append(row)

        seq = 0
        for src_path, src in (("issuerPreviousNameList/previousName", "issuer_previous_name"),
                              ("edgarPreviousNameList/previousName", "edgar_previous_name")):
            for v in all_txt(iss, src_path):
                seq += 1
                names.append({"accession_number": accession, "cik": cik, "seq": seq,
                              "previous_name": v, "source": src})

    # related persons belong to the filing, so they attach to every issuer row
    people = []
    for i, rp in enumerate(children(root, "relatedPersonsList/relatedPersonInfo"), 1):
        people.append({
            "seq": i,
            "first_name":  txt(rp, "relatedPersonName/firstName"),
            "middle_name": txt(rp, "relatedPersonName/middleName"),
            "last_name":   txt(rp, "relatedPersonName/lastName"),
            "street1":     txt(rp, "relatedPersonAddress/street1"),
            "street2":     txt(rp, "relatedPersonAddress/street2"),
            "city":        txt(rp, "relatedPersonAddress/city"),
            "state_or_country":      txt(rp, "relatedPersonAddress/stateOrCountry"),
            "state_or_country_desc": txt(rp, "relatedPersonAddress/stateOrCountryDescription"),
            "zip":         txt(rp, "relatedPersonAddress/zipCode"),
            "relationships": all_txt(rp, "relatedPersonRelationshipList/relationship") or None,
            "relationship_clarification": txt(rp, "relationshipClarification"),
        })
    for f in filings:
        for p in people:
            persons.append(dict(p, accession_number=accession, cik=f["cik"]))

    return filings, persons, names


# ------------------------------------------------------ 3. company history
US_UNKNOWN = None


def parse_history(cik, body):
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


# -------------------------------------------------------------------- main
def business_days(start, end):
    d, out = start, []
    while d <= end:
        out.append(d)
        d += dt.timedelta(days=1)
    return out




def say(msg):
    """Print and flush. Buffered stdout made an 85-minute run look identical to
    a hung one: the log stayed at 0 bytes throughout."""
    print(msg)
    sys.stdout.flush()


def write_day(filings, persons, names, entities):
    """Write one day's work. Called as each day completes rather than once at
    the end, so an interrupted run keeps everything already fetched."""
    fd, pdd, nd = {}, {}, {}
    for f in filings:
        fd[(f["accession_number"], f["cik"])] = f
    for x in persons:
        pdd[(x["accession_number"], x["cik"], x["seq"])] = x
    for x in names:
        nd[(x["accession_number"], x["cik"], x["seq"])] = x
    upsert("filings_raw", list(fd.values()), "accession_number,cik")
    upsert("entities_raw", entities, "cik")
    upsert("filing_related_persons", list(pdd.values()), "accession_number,cik,seq")
    upsert("filing_former_names", list(nd.values()), "accession_number,cik,seq")
    return len(fd), len(entities), len(pdd), len(nd)


def index_accession(path):
    return path.rsplit("/", 1)[-1].replace(".txt", "")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    limit = 0
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])
    if len(args) < 2:
        sys.exit(__doc__)
    start = dt.date.fromisoformat(args[0])
    end = dt.date.fromisoformat(args[1])
    do_priors = "--no-priors" not in flags

    t0 = time.time()
    say("SEC Form D ingest: %s to %s" % (start, end))
    say("User-Agent: %s" % UA)
    say("pacing %.2fs between requests, %d retries on transient failure\n" % (SLEEP, RETRIES))

    # ---- 1. the indexes
    say("1. daily indexes")
    by_day, published, skipped, total_index_entries = {}, 0, 0, 0
    for day in business_days(start, end):
        rows = read_index(day)
        if rows is None:
            skipped += 1
            continue
        published += 1
        by_day[day.isoformat()] = rows
        total_index_entries += len(rows)
        say("   %s %s  %4d Form D" % (day, day.strftime("%a"), len(rows)))
    say("   published index days: %d   no-index days (weekend/holiday): %d"
        % (published, skipped))
    if not total_index_entries:
        sys.exit("No Form D found in the range. Nothing to do.")

    # The index carries one line per issuer, so a filing with co-issuers appears
    # more than once under the same accession. Distinct accessions is the number
    # of actual filings, and it is what completeness is measured against.
    index_accs = {index_accession(r[2]) for rows in by_day.values() for r in rows}
    say("   Form D index lines  : %d" % total_index_entries)
    say("   distinct filings    : %d   (%d lines are co-issuers on a filing already counted)"
        % (len(index_accs), total_index_entries - len(index_accs)))
    held_accs = {a for a, _ in existing_accessions()}
    already = len(index_accs & held_accs)
    if already:
        say("   already stored      : %d of them, and they will not be refetched" % already)

    # ---- 2. per day: filings, then their companies, then write
    say("\n2. filings and companies, written day by day")
    tot = {"filings": 0, "entities": 0, "persons": 0, "names": 0, "fetched": 0}
    missing, seen_ciks, done = [], set(), 0
    for fdate in sorted(by_day):
        rows = by_day[fdate]
        todo = [r for r in rows if index_accession(r[2]) not in held_accs]
        if limit:
            todo = todo[:max(0, limit - tot["fetched"])]
        if not todo:
            say("   %s  nothing to fetch, all %d already held" % (fdate, len(rows)))
            done += 1
            continue

        filings, persons, names = [], [], []
        for iname, cik, path in todo:
            acc = index_accession(path)
            status, xml = fetch(
                "https://www.sec.gov/Archives/edgar/data/%d/%s/primary_doc.xml"
                % (cik, acc.replace("-", "")))
            if status != 200:
                missing.append((acc, cik, "primary_doc HTTP %d" % status))
                continue
            try:
                f, p, n = parse_filing(xml, acc, fdate, iname, path, "daily_index")
            except ET.ParseError as e:
                missing.append((acc, cik, "xml_parse_failed: %s" % e))
                continue
            filings.extend(f)
            persons.extend(p)
            names.extend(n)

        entities = []
        for cik in sorted({f["cik"] for f in filings} - seen_ciks):
            status, body = fetch("https://data.sec.gov/submissions/CIK%010d.json" % cik)
            if status != 200:
                missing.append((str(cik), cik, "submissions HTTP %d" % status))
                continue
            try:
                entities.append(parse_history(cik, body))
                seen_ciks.add(cik)
            except ValueError as e:
                missing.append((str(cik), cik, "json_parse_failed: %s" % e))

        w = write_day(filings, persons, names, entities)
        tot["filings"] += w[0]
        tot["entities"] += w[1]
        tot["persons"] += w[2]
        tot["names"] += w[3]
        tot["fetched"] += sum(1 for f in filings if f["is_primary_issuer"])
        done += 1
        say("   %s  %3d filings, %3d companies, %4d people written   [day %d/%d, %.0f min]"
            % (fdate, w[0], w[1], w[2], done, len(by_day), (time.time() - t0) / 60))

    # ---- 3. rollup priors
    prior_written = 0
    if do_priors:
        hdr = {"apikey": SB_KEY, "Authorization": "Bearer " + SB_KEY}
        known, off = [], 0
        with httpx.Client(timeout=120) as c:
            while True:
                r = c.get("%s/rest/v1/entities_raw" % SB_URL,
                          params={"select": "cik,form_d_history", "limit": "1000",
                                  "offset": str(off)}, headers=hdr)
                page = r.json()
                known.extend(page)
                if len(page) < 1000:
                    break
                off += 1000

        have = {a for a, _ in existing_accessions()}
        want = []
        for e in known:
            hist = [h for h in (e["form_d_history"] or []) if h["form"] == "D"]
            if len(hist) < 2:
                continue
            newest = dt.date.fromisoformat(max(h["filing_date"] for h in hist))
            for h in hist:
                if h["accession"] in have:
                    continue
                if (newest - dt.date.fromisoformat(h["filing_date"])).days <= ROLLUP_DAYS:
                    want.append((e["cik"], h["accession"], h["filing_date"]))

        say("\n3. rollup priors: %d prior Form D inside %d days and not already held"
            % (len(want), ROLLUP_DAYS))
        pf, pp, pn = [], [], []
        for i, (cik, acc, fdate) in enumerate(want, 1):
            status, xml = fetch(
                "https://www.sec.gov/Archives/edgar/data/%d/%s/primary_doc.xml"
                % (cik, acc.replace("-", "")))
            if status != 200:
                missing.append((acc, cik, "prior primary_doc HTTP %d" % status))
                continue
            try:
                f, p, n = parse_filing(xml, acc, fdate, None, None, "rollup_prior")
            except ET.ParseError as e:
                missing.append((acc, cik, "prior xml_parse_failed: %s" % e))
                continue
            pf.extend(f)
            pp.extend(p)
            pn.extend(n)
            if i % 50 == 0 or i == len(want):
                say("   %d/%d" % (i, len(want)))
        if pf:
            prior_written = write_day(pf, pp, pn, [])[0]
        say("   prior filing rows written: %d" % prior_written)
    else:
        say("\n3. rollup priors: skipped (--no-priors)")

    # ---- verification
    say("\n--- verification ---")
    say("index lines in window       : %d" % total_index_entries)
    say("distinct filings to store   : %d" % len(index_accs))
    say("held from an earlier run    : %d" % already)
    say("fetched this run            : %d" % tot["fetched"])
    say("prior filings added         : %d" % prior_written)
    say("requests made               : %d" % STATS["req"])
    say("transient retries           : %d" % STATS["retried"])
    say("gave up after retrying      : %d" % STATS["gave_up"])
    say("http errors                 : %s" % (STATS["http_err"] or "none"))
    say("elapsed                     : %.1f min" % ((time.time() - t0) / 60))
    say("cost                        : $0")
    say("")
    for t in ("filings_raw", "entities_raw", "filing_related_persons",
              "filing_former_names"):
        say("table %-24s %d rows" % (t, table_count(t)))

    now_held = {a for a, _ in existing_accessions()}
    short = len(index_accs - now_held)
    if missing or (short and not limit):
        say("\nINCOMPLETE PULL")
        for r in missing[:20]:
            say("   %s" % (r,))
        if short:
            say("   %d distinct filings have no row in filings_raw" % short)
        say("\nEvery write is an idempotent upsert and the run skips what is already")
        say("stored, so re-running costs only the missing documents.")
        sys.exit(1)

    say("\nCOMPLETE: %d of %d distinct filings in filings_raw, no gaps."
        % (len(index_accs & now_held), len(index_accs)))


if __name__ == "__main__":
    main()
