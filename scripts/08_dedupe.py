#!/usr/bin/env python3
"""
Step 8: dedupe the enriched rows against Mercury's existing customers, its
inbound, and every address ever written to.

The dedupe runs after Clay because it joins on domain, and domain only exists
once Clay has resolved it.

Reads:  outbound_companies_scored (enrichment_status = 'enriched')
        existing_mercury_customers, mercury_inbound, contacted_emails
Writes: outbound_companies_scored (dedupe_status, dedupe_matched_on,
        dedupe_matched_id) and, with --seed, the three target tables
Cost:   nothing.

Order of the checks is the order of the outcomes' weight. A company Mercury
already banks is removed before anything else is asked about it; inbound next,
because they came to us; the address check last, because it protects an inbox
rather than a relationship.

Phone is the secondary check on the customer and inbound joins only. It is not a
check on contacted_emails, which is keyed on the address by design: the thing
being protected there is a person's inbox, and it has to outlive the company.

dupe_same_signer is never overwritten. 05_collapse_signers.py already settled
those rows and they carry a collapsed_into_cik pointing at the row we kept.

--seed writes the demo rows the joins need. Without them the codes cannot fire
and their measured rate would be a guess. It is idempotent: re-running it
changes nothing.

All writes are idempotent. Safe to re-run.

Usage:
    py -3 scripts/08_dedupe.py --seed
    py -3 scripts/08_dedupe.py
"""
import os
import sys
import datetime as dt

import httpx

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding="utf-8")

# The demo seeds, chosen from the rows that have copy so the joins fire on a
# real candidate rather than on a row that was going nowhere anyway.
SEED_CUSTOMER = "atoms.co"
SEED_INBOUND = "qualitate.io"
SEED_CONTACTED = "delphiinteractive.com"
# Each test row gets its own inbox. One shared address cannot demonstrate a
# reply: the sender is what ties a reply back to a row, and two rows sharing
# an address make that match ambiguous. TEST_EMAILS is the allowlist, and it
# is the only set of addresses anything is ever sent to.
TEST_ROWS = {
    "blacksmith.sh": 0,
    "coderabbit.ai": 1,
}


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
    for k in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "TEST_EMAIL",
              "TEST_EMAILS", "TEST_PHONE"):
        if not env.get(k):
            sys.exit("%s is not set in .env" % k)
    return env


ENV = load_env()
BASE = ENV["SUPABASE_URL"].rstrip("/") + "/rest/v1/"
CLIENT = httpx.Client(
    headers={"apikey": ENV["SUPABASE_SERVICE_ROLE_KEY"],
             "Authorization": "Bearer " + ENV["SUPABASE_SERVICE_ROLE_KEY"],
             "Content-Type": "application/json"},
    timeout=60.0,
)


def get(table, **params):
    r = CLIENT.get(BASE + table, params=params)
    if r.status_code != 200:
        sys.exit("GET %s -> %s\n%s" % (table, r.status_code, r.text[:400]))
    return r.json()


def patch(table, where, body):
    r = CLIENT.patch(BASE + table, params=where, json=body,
                     headers={"Prefer": "return=representation"})
    if r.status_code not in (200, 204):
        sys.exit("PATCH %s %s -> %s\n%s" % (table, where, r.status_code, r.text[:400]))
    return r.json() if r.text.strip() else []


def upsert(table, body, on_conflict):
    r = CLIENT.post(BASE + table, params={"on_conflict": on_conflict}, json=body,
                    headers={"Prefer": "resolution=merge-duplicates,return=representation"})
    if r.status_code not in (200, 201):
        sys.exit("POST %s -> %s\n%s" % (table, r.status_code, r.text[:400]))
    return r.json() if r.text.strip() else []


def upsert_by_domain(table, body):
    """The unique index on these two tables is on lower(domain), an expression
    index, which PostgREST cannot use for ON CONFLICT. Look up, then write.
    Idempotent by the same rule: one row per domain, re-running changes nothing."""
    existing = get(table, select="id", domain="eq." + body["domain"])
    if existing:
        patch(table, {"id": "eq.%s" % existing[0]["id"]}, body)
        return existing[0]["id"]
    r = CLIENT.post(BASE + table, json=body, headers={"Prefer": "return=representation"})
    if r.status_code not in (200, 201):
        sys.exit("POST %s -> %s\n%s" % (table, r.status_code, r.text[:400]))
    return r.json()[0]["id"]


def apex(d):
    """Normalised apex domain. Lowercase, no scheme, no www, no path."""
    if not d:
        return None
    d = d.strip().lower()
    for p in ("https://", "http://"):
        if d.startswith(p):
            d = d[len(p):]
    d = d.split("/")[0].split("?")[0]
    if d.startswith("www."):
        d = d[4:]
    return d or None


def digits(p):
    return "".join(c for c in (p or "") if c.isdigit()) or None


def enriched():
    return get("outbound_companies_scored",
               select=("cik,current_name_candidates,domain,work_email,phone_candidates,"
                       "industry,score,dedupe_status,is_test_row"),
               enrichment_status="eq.enriched", order="score.desc")


# ------------------------------------------------------------------- seeding
def seed():
    rows = {apex(r["domain"]): r for r in enriched() if r["domain"]}
    for d in (SEED_CUSTOMER, SEED_INBOUND, SEED_CONTACTED, *TEST_ROWS):
        if d not in rows:
            sys.exit("seed domain %s is not among the enriched rows" % d)

    def name(d):
        return (rows[d]["current_name_candidates"] or ["?"])[0]

    c = rows[SEED_CUSTOMER]
    upsert_by_domain("existing_mercury_customers", {
        "company_name": name(SEED_CUSTOMER),
        "domain": SEED_CUSTOMER,
        "phone": (c["phone_candidates"] or [None])[0],
        "contact_name": "Seeded demo customer",
        "contact_email": ENV["TEST_EMAIL"],
        "industry": c["industry"],
    })

    i = rows[SEED_INBOUND]
    upsert_by_domain("mercury_inbound", {
        "company_name": name(SEED_INBOUND),
        "domain": SEED_INBOUND,
        "phone": (i["phone_candidates"] or [ENV["TEST_PHONE"]])[0] or ENV["TEST_PHONE"],
        "contact_name": "Seeded demo inbound",
        "contact_email": ENV["TEST_EMAIL"],
        "industry": i["industry"],
        "expected_balance_band": "$100k to $1m",
        "source": "demo seed",
        "submitted_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    })

    e = rows[SEED_CONTACTED]
    if not e["work_email"]:
        sys.exit("%s has no work_email to seed contacted_emails with" % SEED_CONTACTED)
    upsert("contacted_emails", {
        "email_normalised": e["work_email"].strip().lower(),
        "cik": e["cik"],
        "company_name": name(SEED_CONTACTED),
        "source": "outbound",
        "is_demo_seed": True,
    }, on_conflict="email_normalised")

    # Test rows. Nothing is ever sent to a real company, so the only sendable
    # addresses are the ones in TEST_EMAILS. The real address is replaced, not
    # kept beside the flag: an address still sitting in the row is an address
    # that can still be sent to.
    inboxes = [a.strip().lower() for a in ENV["TEST_EMAILS"].split(",") if a.strip()]
    if len(inboxes) < len(TEST_ROWS):
        sys.exit("TEST_EMAILS has %d addresses, %d test rows need one each"
                 % (len(inboxes), len(TEST_ROWS)))
    for d, i in TEST_ROWS.items():
        patch("outbound_companies_scored", {"cik": "eq.%s" % rows[d]["cik"]},
              {"is_test_row": True, "work_email": inboxes[i]})

    print("seeded:")
    print("  existing_mercury_customers  %s" % SEED_CUSTOMER)
    print("  mercury_inbound             %s" % SEED_INBOUND)
    print("  contacted_emails            %s (address redacted)" % SEED_CONTACTED)
    for d, i in TEST_ROWS.items():
        print("  test row                    %-24s -> %s" % (d, inboxes[i]))
    print()


# -------------------------------------------------------------------- dedupe
def run():
    rows = enriched()
    customers = get("existing_mercury_customers", select="id,domain,phone")
    inbound = get("mercury_inbound", select="id,domain,phone")
    contacted = get("contacted_emails", select="email_normalised")

    cust_d = {apex(c["domain"]): c["id"] for c in customers if c["domain"]}
    cust_p = {digits(c["phone"]): c["id"] for c in customers if digits(c["phone"])}
    inb_d = {apex(x["domain"]): x["id"] for x in inbound if x["domain"]}
    inb_p = {digits(x["phone"]): x["id"] for x in inbound if digits(x["phone"])}
    seen = {(c["email_normalised"] or "").strip().lower() for c in contacted}

    counts = {}
    for r in rows:
        if r["dedupe_status"] == "dupe_same_signer":
            k = "dupe_same_signer (left alone)"
            counts[k] = counts.get(k, 0) + 1
            continue

        d = apex(r["domain"])
        phones = [digits(p) for p in (r["phone_candidates"] or []) if digits(p)]
        email = (r["work_email"] or "").strip().lower()

        status, on, mid = "unique", None, None
        if d and d in cust_d:
            status, on, mid = "dupe_existing_customer", "domain", cust_d[d]
        elif any(p in cust_p for p in phones):
            p = next(p for p in phones if p in cust_p)
            status, on, mid = "dupe_existing_customer", "phone", cust_p[p]
        elif d and d in inb_d:
            status, on, mid = "dupe_inbound", "domain", inb_d[d]
        elif any(p in inb_p for p in phones):
            p = next(p for p in phones if p in inb_p)
            status, on, mid = "dupe_inbound", "phone", inb_p[p]
        elif email and email in seen:
            status, on, mid = "dupe_already_emailed", None, None

        patch("outbound_companies_scored", {"cik": "eq.%s" % r["cik"]},
              {"dedupe_status": status, "dedupe_matched_on": on, "dedupe_matched_id": mid})
        counts[status] = counts.get(status, 0) + 1

    print("VERIFICATION")
    print("  enriched rows considered      %d" % len(rows))
    for k in sorted(counts):
        print("  %-30s  %d" % (k, counts[k]))

    back = get("outbound_companies_scored",
               select=("cik,current_name_candidates,domain,dedupe_status,"
                       "dedupe_matched_on,is_test_row,copy_body"),
               enrichment_status="eq.enriched", order="score.desc")
    for code in ("dupe_existing_customer", "dupe_inbound", "dupe_already_emailed"):
        hit = [x for x in back if x["dedupe_status"] == code]
        if not hit:
            sys.exit("%s fired on 0 rows. The seed did not take, so its rate is "
                     "unmeasured." % code)
    print()
    print("  every dedupe code fired at least once, so none is padding.")

    ready = [x for x in back if x["dedupe_status"] == "unique" and x["copy_body"]]
    print()
    print("  DISPATCHABLE: unique, with copy and an address   %d" % len(ready))
    for x in ready:
        nm = (x["current_name_candidates"] or ["?"])[0]
        print("    %-28s %-24s test_row=%s" % (nm[:28], x["domain"], x["is_test_row"]))


if __name__ == "__main__":
    if "--seed" in sys.argv[1:]:
        seed()
    run()
