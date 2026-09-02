#!/usr/bin/env python3
"""
Step 7: export the Clay payload as CSV.

Reads outbound_companies_scored and writes exports/, which is gitignored
because it holds real contact data. Nothing is sent anywhere; this produces
the file an operator uploads to Clay, because the free tier has no HTTP API
column.

Columns are the payload named in the source of truth, in that order, plus
rolled_filing_count (changelog 16) so a summed amount is never read as a
single raise, and also_signed_for (changelog 23) naming the other companies
the same person signed for, which sits beside contact_name because it is a
fact about that person. website_from_edgar is not exported: it is empty on all
830 scored companies (changelog 27).

ONLY ROWS THAT SURVIVED THE SIGNER COLLAPSE ARE EXPORTED. A row marked
dupe_same_signer is one of 19 Imagen entities signed by the same human, and
sending all 19 to Clay would spend enrichment on 19 names to reach one inbox.
Run scripts/05_collapse_signers.py first, or this refuses to start.

EVERY COLUMN IS PLAIN TEXT. Clay reads a CSV cell, and no column it runs an
action or a formula on should have to be unpacked first, so the arrays and the
people JSON are flattened here rather than in Clay (changelog 21):

  people        Jane Doe (Executive Officer); John Roe (Director, Promoter)
  candidates    Acme Inc.; Acme Corporation
  amounts       plain numbers, no symbols or separators, so a formula can add
                them without stripping anything first
  empty         an empty cell, never the string "None" or "null"

Multi-value cells use "; " throughout. Commas are left inside addresses and
titles where they belong, and the csv module quotes any field containing one.

Two files are written:
  clay_payload_<date>.csv       all scored companies, highest score first
  clay_payload_<date>_top200.csv the first 200 of them, because a Clay free
                                 table holds 200 rows

Which rows actually cross into Clay is the enrichment-gate decision and is not
made here: this script does not touch enrichment_status, so nothing is marked
not_selected behind your back.

Usage:
    python scripts/05_export_clay_csv.py
"""
import os
import re
import csv
import sys
import json
import time
import datetime as dt

import httpx

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORTS = os.path.join(ROOT, "exports")
CLAY_FREE_ROWS = int(sys.argv[sys.argv.index("--top") + 1]) if "--top" in sys.argv else 200
SEP = "; "

# Values a filing puts in a box to mean 'nothing'. They are not data and must
# never reach Clay as something to chase.
JUNK = ("None", "null", "[]", "{}", "N/A", "n/a", "NA", "none",
        "unknown", "Unknown", "TBD", "-")

# The order the work is done in, because a person reads these left to right in a
# Clay table: the key and the priority, then who and what to search for, then the
# evidence that confirms an answer, then the facts the copy is built from.
# also_signed_for sits beside contact_name because it is a fact about that
# person, not about this company.
# website_from_edgar is deliberately absent: measured empty on all 830 scored
# companies, so it was 200 blank cells. The column stays in Supabase.
COLUMNS = [
    "cik",
    "score",
    "current_name",
    "former_names",
    "contact_name",
    "also_signed_for",
    "people",
    "address_candidates",
    "phone_candidates",
    "industry",
    "amount_sold",
    "amount_remaining",
    "rolled_filing_count",
    "prior_formd_count",
    "filing_date",
]


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


# ----------------------------------------------------------------- flatten
def text(v):
    """A cell. None becomes empty, never the string 'None'."""
    return "" if v is None else str(v)


def joined(values):
    """A list column as one plain string."""
    if not values:
        return ""
    return SEP.join(str(v).strip() for v in values if v is not None and str(v).strip())


def flat_people(people):
    """[{name, relationships}] -> 'Jane Doe (Executive Officer); John Roe (Director, Promoter)'.

    The relationship is what tells Clay, and the copy, whether the human is an
    officer worth writing to or a promoter who is not."""
    if not people:
        return ""
    if isinstance(people, str):
        try:
            people = json.loads(people)
        except ValueError:
            return people
    out = []
    for p in people:
        name = (p.get("name") or "").strip()
        if not name:
            continue
        rels = [r for r in (p.get("relationships") or []) if r]
        out.append("%s (%s)" % (name, ", ".join(rels)) if rels else name)
    return SEP.join(out)


# Tokens that stay shouting when a SHOUTED field is calmed down: legal suffixes,
# US state and country codes, and the directional and ordinal scraps of an
# address. Anything containing a digit is left exactly as filed, so DS1 and
# 169 do not become Ds1 and 169th by accident.
KEEP_UPPER = {
    "LLC", "L.L.C.", "LLP", "LP", "L.P.", "PLLC", "INC", "INC.", "CORP", "CORP.",
    "PBC", "PC", "PA", "CO", "CO.", "LTD", "LTD.", "GP", "SPV", "REIT", "USA",
    "US", "UK", "AI", "IT", "HQ", "PO", "II", "III", "IV", "V", "VI",
    "N", "S", "E", "W", "NE", "NW", "SE", "SW", "NY", "CA", "TX", "FL", "DE",
    "IL", "MA", "WA", "CO", "GA", "NC", "NJ", "PA", "VA", "AZ", "MI", "OH",
    "MO", "MN", "MD", "TN", "IN", "WI", "OR", "SC", "AL", "KY", "LA", "OK",
    "CT", "UT", "IA", "NV", "AR", "MS", "KS", "NM", "NE", "WV", "ID", "HI",
    "NH", "ME", "MT", "RI", "SD", "ND", "AK", "VT", "WY", "DC", "PR",
}


def _calm_words(seg):
    out = []
    for tok in seg.split(" "):
        bare = tok.strip(",.()")
        if not bare or any(c.isdigit() for c in bare) or bare.upper() in KEEP_UPPER:
            out.append(tok)
        elif "-" in tok:
            out.append("-".join(w.capitalize() for w in tok.split("-")))
        else:
            out.append(tok.capitalize())
    return " ".join(out)


def calm(value):
    """Take the shouting out of the parts of a field that arrived in capitals.

    Filers type into a form and many of them use caps lock. SAGAR KADAKIA and
    1 LIBERTY STREET read worse than Sagar Kadakia and 1 Liberty Street, and a
    name in capitals also looks like an acronym.

    Applied per comma-separated SEGMENT, not per field and not per word. A
    segment is only calmed when it is entirely uppercase, so a real acronym in
    ordinary text survives: FSH Technologies keeps its FSH because that segment
    is mixed case, while NEW YORK sitting beside a title-cased street does not,
    which a whole-field test missed. Within a calmed segment a token holding a
    digit, a legal suffix or a state code is left alone, so DS1, LLC and NY
    stay as filed.

    Presentation only, and it happens on export. Supabase keeps what the filing
    said.
    """
    if not value:
        return value
    parts = []
    for seg in value.split(", "):
        parts.append(seg if any(c.islower() for c in seg) else _calm_words(seg))
    return ", ".join(parts)


def calm_person(entry):
    """A people entry is 'NAME (Relationship, Relationship)'. Only the name is
    calmed, so CRISSY BEHRENS (Director) does not keep half its shouting."""
    if " (" not in entry:
        return calm(entry)
    name, rest = entry.split(" (", 1)
    return calm(name) + " (" + rest


def phone(raw):
    """One written format, because five is not a format.

    The filings carry one number five ways: 650-549-1400, (650) 549-1400,
    6505491400, 650.549.1400 and worse. Claygent reads them all alike, but
    the post-Clay dedupe compares phones as strings, and two spellings of
    one number match nothing while reporting success. A missed dedupe means
    emailing an existing customer.

    Every value is digits only, country code first, and nothing else. A US
    number gains its leading 1 so it has the same shape as the rest.

    No plus sign, and that is deliberate rather than untidy. A plus asserts the
    digits after it are a real country code, which is only knowable for the US
    ones here: 44 7835 097 128 is a genuine UK number but 757-434-25343 is a
    typo, and prefixing both would turn the typo into a confident claim about
    Russia. Digits alone assert nothing, compare exactly, and a dialler can add
    the plus once a country is known.
    """
    d = re.sub(r"[^0-9]", "", raw or "")
    if len(d) == 10:
        d = "1" + d
    return d


def phones(values):
    out, seen = [], set()
    for v in values or []:
        f = phone(v)
        if f and f not in seen:
            seen.add(f)
            out.append(f)
    return SEP.join(out)


def money(v):
    """Plain number, no symbol and no thousands separator, so a Clay formula can
    add it without stripping anything first."""
    if v is None:
        return ""
    return ("%.2f" % float(v)).rstrip("0").rstrip(".")


def main():
    t0 = time.time()
    say("Export the Clay payload as CSV\n")

    all_rows = get_all(
        "outbound_companies_scored",
        "cik,current_name_candidates,former_name_candidates,address_candidates,"
        "phone_candidates,website_from_edgar,contact_name,people,amount_sold,"
        "amount_remaining,industry,prior_formd_count,rolled_filing_count,"
        "also_signed_for,dedupe_status,filing_date,score")
    if not all_rows:
        sys.exit("outbound_companies_scored is empty. Run scripts/04_score.py first.")

    collapsed = [r for r in all_rows if r["dedupe_status"] == "dupe_same_signer"]
    rows = [r for r in all_rows if r["dedupe_status"] != "dupe_same_signer"]
    if not collapsed:
        sys.exit("No row is marked dupe_same_signer. Run scripts/05_collapse_signers.py "
                 "first, or 19 companies belonging to one person go to Clay.")
    rows.sort(key=lambda r: (-(float(r["score"] or 0)), r["cik"]))
    say("read %d scored companies" % len(all_rows))
    say("   %d held back as the same person, %d exported" % (len(collapsed), len(rows)))

    out = []
    for r in rows:
        out.append({
            "cik": text(r["cik"]),
            "current_name": calm(joined(r["current_name_candidates"])),
            "former_names": calm(joined(r["former_name_candidates"])),
            "address_candidates": calm(joined(r["address_candidates"])),
            "phone_candidates": phones(r["phone_candidates"]),
            "contact_name": calm(text(r["contact_name"])),
            "people": SEP.join(calm_person(x) for x in flat_people(r["people"]).split(SEP)),
            "amount_sold": money(r["amount_sold"]),
            "amount_remaining": money(r["amount_remaining"]),
            "industry": text(r["industry"]),
            "prior_formd_count": text(r["prior_formd_count"]),
            "rolled_filing_count": text(r["rolled_filing_count"]),
            "also_signed_for": SEP.join(calm(x) for x in joined(r["also_signed_for"]).split(SEP)),
            "filing_date": text(r["filing_date"]),
            "score": text(r["score"]),
        })

    os.makedirs(EXPORTS, exist_ok=True)
    stamp = dt.date.today().isoformat()
    full = os.path.join(EXPORTS, "clay_payload_%s.csv" % stamp)
    top = os.path.join(EXPORTS, "clay_payload_%s_top%d.csv" % (stamp, CLAY_FREE_ROWS))

    for path, subset in ((full, out), (top, out[:CLAY_FREE_ROWS])):
        with open(path, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=COLUMNS, quoting=csv.QUOTE_MINIMAL)
            w.writeheader()
            w.writerows(subset)
        say("wrote %-52s %4d rows, %6.1f KB"
            % (os.path.relpath(path, ROOT), len(subset), os.path.getsize(path) / 1024.0))

    # ---- verification ----------------------------------------------------
    say("\n--- verification ---")
    say("columns: %d, in payload order" % len(COLUMNS))
    say("   %s" % ", ".join(COLUMNS))

    bad_type = []
    for i, row in enumerate(out):
        for k, v in row.items():
            if not isinstance(v, str):
                bad_type.append((i, k, type(v).__name__))
    say("non-text cells: %d (must be 0)" % len(bad_type))
    if bad_type:
        sys.exit("a cell reached the CSV as something other than text: %s" % bad_type[:5])

    leaked = [(r["cik"], k) for r in out for k, v in r.items()
              if v in JUNK]
    say("cells holding a literal None/null/[]/{}: %d (must be 0)" % len(leaked))
    if leaked:
        sys.exit("a placeholder leaked into the CSV: %s" % leaked[:5])

    vals = [v for r in out for v in r["phone_candidates"].split(SEP) if v]
    us = sum(1 for v in vals if len(v) == 11 and v.startswith("1"))
    say("")
    say("phones, all digits only, country code first           : %d" % len(vals))
    say("   of those, US (11 digits starting 1)                : %d" % us)
    say("   non-US or malformed, left exactly as their digits  : %d" % (len(vals) - us))
    bad = [v for v in vals if not v.isdigit()]
    say("   containing anything other than a digit             : %d (must be 0)" % len(bad))
    if bad:
        sys.exit("a phone reached the CSV with punctuation in it: %s" % bad[:5])
    say("\nfill rate per column:")
    for c in COLUMNS:
        n = sum(1 for r in out if r[c])
        say("   %-26s %4d of %d (%3.0f%%)" % (c, n, len(out), 100.0 * n / len(out)))

    say("\nfirst 3 rows, people and candidates as Clay will see them:")
    for r in out[:3]:
        say("   %s  score %s" % (r["current_name"][:40], r["score"]))
        say("      contact_name : %s" % (r["contact_name"] or "(blank, agent)"))
        say("      people       : %s" % (r["people"][:100] or "(none)"))
        say("      address      : %s" % (r["address_candidates"][:100] or "(none)"))
        say("      phone        : %s" % (r["phone_candidates"] or "(none)"))

    say("\nelapsed: %.1f min" % ((time.time() - t0) / 60))
    say("cost: $0")
    say("\nCOMPLETE. Nothing uploaded: enrichment_status is untouched, so no row")
    say("is marked not_selected until the enrichment gate is decided.")


if __name__ == "__main__":
    main()
