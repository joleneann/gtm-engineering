# Mercury GTM Engineering build

A cold outreach system that finds companies at the moment they raise money, scores them, enriches
them, writes the email, and runs the CRM leg end to end.

The trigger is SEC Form D. Every US company raising private capital files one within fifteen days of
its first sale, so it is a daily, free, machine-readable feed of the exact event that reopens the
business banking question. Mercury's own homepage defines its market as companies that just raised.

Python ingests and scores. Supabase is the truth layer. Clay enriches and writes the copy. n8n is the
conveyor belt into Pipedrive and back out to Gmail.

**`docs/source_of_truth.md` is the authority on every fact in this build.** This file is the short
version and defers to it wherever the two could be read differently.

---

## What it did, measured 2026-09-04

Twenty days of filings, read from `v_funnel`:

| Stage | Reason | Companies | % of ingested |
|---|---|---|---|
| ingested | | 3,512 | 100 |
| routed out | `scope_pooled_investment_fund` | 1,996 | 56.83 |
| routed out | `scope_non_us_incorporation` | 232 | 6.61 |
| routed out | `scope_unsupported_country` | 106 | 3.02 |
| parked | `scope_industry_other` | 346 | 9.85 |
| **scored** | | **830** | **23.63** |
| held back | `dupe_same_signer` | 30 | 0.85 |
| never sent to Clay | `free_tier_row_cap` | 784 | 22.32 |
| enrichment failed | `enrich_no_work_email` | 3 | 0.09 |
| enriched | | 13 | 0.37 |
| removed | the three dedupe codes | 1 each | 0.03 each |
| **has copy** | | **5** | **0.14** |

The stages after `scored` add to 830 exactly: 30 + 784 + 3 + 13. Nothing is deleted anywhere in the
pipeline; every company that leaves carries the code that removed it.

The CRM leg, read from `v_outreach`:

| Stage | Deals | Test | Real | Sent | Replied |
|---|---|---|---|---|---|
| enriched | 3 | 0 | 3 | 0 | 0 |
| replied | 2 | 2 | 0 | 2 | 2 |

**Zero real companies were emailed, and that is enforced rather than promised.** A row whose address
is not in the `TEST_EMAILS` allowlist stops the workflow with an error. Real companies stop at
Enriched with the drafted subject and body attached to a Pipedrive task, for a human to send or not.

## How it works

1. **Ingest.** Three public SEC endpoints, no key, no scraping: the day's filing index, each Form D
   XML, each company's filing history JSON. Every field becomes a column, so a field ruled out today
   can be used tomorrow without refetching.
2. **Route.** Funds out (industry group or the pooled-fund tick; either alone leaks). Companies
   Mercury cannot serve out, on incorporation and address. `Other` industry parked, not discarded.
3. **Score.** Out of 10: amount sold 5, amount remaining 1, industry 3, prior filings 1. Filings by
   one company inside a rolling 12 months are added up first, so a summed figure is never read as one
   raise.
4. **Collapse.** One human signing for more than three companies gets one email, not one per company.
   Measured: 4 signers covering 34 companies named 7 humans between them.
5. **Enrich.** Clay resolves the domain and the work email, and Claygent writes the copy from a signal
   on the company's own site, never from the funding round. The prompt is versioned at
   `prompts/claygent_copy.md`.
6. **Dedupe, then run.** Joins on apex domain against existing customers, inbound, and every address
   ever written to. Then n8n creates the Pipedrive objects, sends only to test rows, catches the
   reply, and moves the deal.

## The repository

| Path | What it is |
|---|---|
| `docs/source_of_truth.md` | The only record of what this system is and does |
| `docs/sources/` | Verbatim evidence captures, each with its fetch date and command |
| `db/schema.sql` | The single source of truth for the database |
| `db/migration_*.sql`, `db/revert_*.sql` | Every change applied since, each with its revert |
| `scripts/` | One script per step, numbered |
| `n8n/` | The three workflows as JSON |
| `prompts/` | The Claygent copy prompt |
| `exports/`, `.env` | Gitignored. Real contact data and secrets never enter the repository |

### Scripts, in order

| Script | Reads | Writes |
|---|---|---|
| `00_doc_check.py` | every file under `docs/`, `CLAUDE.md`, `README.md` | nothing. Fails if a withdrawn phrase is live |
| `01_ingest_form_d.py` | SEC daily index, Form D XML, submissions JSON | `filings_raw` + 2 child tables, `entities_raw` |
| `02_route.py` | `filings_raw`, `entities_raw` | `formd_funds`, `likely_unserviceable_companies`, `no_industry_companies`, `outbound_companies_unscored` |
| `03_build_mill_list.py` | `filings_raw` | `mill_list`: addresses and phones shared by more than three distinct companies |
| `04_score.py` | `outbound_companies_unscored` and friends | `outbound_companies_scored`, one row per company, payload included |
| `05_collapse_signers.py` | `outbound_companies_unscored`, `outbound_companies_scored` | `signer_list`, and marks `dupe_same_signer` |
| `06_export_clay_csv.py` | `outbound_companies_scored` | `exports/clay_payload_<date>.csv`, plus a 200-row file for the free tier |
| `07_import_clay_results.py` | `exports/clay_payload-enriched.csv` | `outbound_companies_scored`: domain, email, subject, copy, status |
| `08_dedupe.py` | the enriched rows, the three target tables | dedupe status; `--seed` writes the demo rows the codes need |
| `09_pipedrive_probe.py` | Pipedrive, read-only | `docs/sources/pipedrive_fields_<date>.md`: the 40-character field keys |
| `10_install_n8n.py` | `n8n/*.json`, `.env` | credentials and workflows in the local n8n |
| `11_reset_demo.py` | Pipedrive, Supabase | clears the CRM leg so the demo can be run again from nothing |
| `13_install_workflow_offline.py` | one workflow file | that workflow in n8n's SQLite, with n8n stopped |

Every script is an idempotent upsert and safe to re-run. Each asserts its own completeness and fails
loudly rather than ending partway: there is no dead-letter table and no run log, because re-running is
free.

Step 12 was an IMAP repair and is deleted. It patched a node the reply workflow no longer has, and
running it today would break the workflow that replaced it.

### The three workflows

- **GTME 1, outbound run.** Fetches only rows whose `pipedrive_deal_id` is null, so idempotency is a
  query rather than a find-or-create search. Creates Organization, Person and Deal, writes all three
  ids back the moment each exists, then branches: a test row is emailed and moves to Emailed, a real
  company gets a task holding the drafted email and stays at Enriched.
- **GTME 2, reply catcher.** Reads Gmail over OAuth, scoped by a sender query. Matches the sender
  against a row already at stage Emailed, moves that deal to Replied, stamps `replied_at`. A reply
  from someone we never wrote to matches nothing and ends quietly.
- **GTME 3, flywheel.** Won deals become rows in `existing_mercury_customers`, so the next Form D from
  that company is deduped out instead of emailed.

Credentials live in n8n, never in these files: the workflows carry the placeholders `SUPABASE_CRED`,
`PIPEDRIVE_CRED` and `GMAIL_CRED`, resolved at install time. There is no webhook anywhere, because a
self-hosted webhook needs a public URL and a tunnel gets a new address every restart.

## Running it

```bash
py -3 scripts/01_ingest_form_d.py 2026-08-05 2026-09-01
py -3 scripts/02_route.py
py -3 scripts/03_build_mill_list.py
py -3 scripts/04_score.py
py -3 scripts/05_collapse_signers.py
py -3 scripts/06_export_clay_csv.py
# upload the CSV to Clay, run the table, export the result to exports/
py -3 scripts/07_import_clay_results.py
py -3 scripts/08_dedupe.py --seed && py -3 scripts/08_dedupe.py
./run_n8n.sh    # then press Execute on GTME 1, reply to the mail, Execute on GTME 2
py -3 scripts/00_doc_check.py
```

Schema is applied by hand through the Supabase SQL editor from the versioned file, never by a script
and never through MCP. Supabase MCP is read-only and for inspection.

## The rules this build holds itself to

- **Budget is $0.** Nothing here requires payment. Clay's free tier is the binding constraint and it
  is where 784 companies stopped, which is recorded as a budget boundary rather than dressed up as an
  enrichment failure.
- **Nothing is ever sent to a real company.** Enforced by a node that fails the run, not by
  convention.
- **A decision is not made until it is written.** `scripts/00_doc_check.py` reads every live document
  in full and fails if a superseded phrase has crept back in.
- **Schema is law.** No table or column exists that `db/schema.sql` does not name.
- **Every number is measured.** No count, rate or ranking appears anywhere until a script has produced
  it, and a figure is labelled quoted or derived.
- **A missing value is not a disqualification.** Nulls route out with a code and are counted.

## What this build cannot report

Reply rate, open rate, deliverability, cost per lead, the domain resolution rate, and the natural
dedupe rates. The replies are its own test emails; there is no open tracking, deliberately, because a
pixel or a redirect domain is what harms deliverability; nothing was paid for, so there is no cost
table; 16 of 50 domains is where the free tier stopped, not a resolution rate; and all three dedupe
codes fired against seeded rows. A view reporting any of them would be reporting a number nobody
measured.
