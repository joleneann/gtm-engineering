# Source of truth: Mercury GTM Engineering build

This is the only current record of the system. Everything in `archive/` predates it and is wrong.
The original hand-written document is preserved untouched at `archive/sourceoftruth_2026-09-02.docx`.

**A decision is not made until it is written here.** See the no-drift rule in `CLAUDE.md`.

## Changelog

Every row is a change made to the original document, with the phrase it withdrew. A withdrawn phrase
must never reappear in `docs/` or `CLAUDE.md`; `scripts/00_doc_check.py` enforces that.

| # | Date | Change | Withdrawn phrase |
|---|---|---|---|
| 1 | 2026-09-02 | Table renamed: it holds companies, not countries, and the spelling was wrong | `likelyunservicable_countries` |
| 2 | 2026-09-02 | Customer table renamed | `existing_company_customers` |
| 3 | 2026-09-02 | Inbound table renamed | `inbound_companies` |
| 4 | 2026-09-02 | `industryGroupType` is never null; these companies declared `Other`, and they are 18-24% of operating companies, not a small share. Measured 0/193 and 0/165 null; 13/73 and 15/62 `Other` | `have not declared an industry type` |
| 5 | 2026-09-02 | Multi-filing rollup window fixed to a rolling 12 months on `filingDate`, anchored on the newest filing. Non-amount fields come from the newest filing | `within a financial year` |
| 6 | 2026-09-02 | Four tables added that the original does not name: `filing_related_persons`, `filing_former_names`, `industry_scores`, `industry_clusters` | |
| 7 | 2026-09-02 | Storage made explicit: every field of the document becomes a column, not a blob | `get written whole into Supabase` |
| 8 | 2026-09-02 | Dedupe runs after Clay, on normalised apex domain with phone as a secondary check. Neither customer table carries a CIK | |
| 9 | 2026-09-02 | `website` from the submissions JSON is sent to Clay. `investorWebsite` is not: it is an investor-relations URL, not the company domain | |
| 10 | 2026-09-02 | Servicability check moved ahead of the `Other` industry park, so a parked company is already known serviceable | |
| 11 | 2026-09-02 | Seed rows fixed at 3 existing customers, 2 inbound, 2 test rows on `TEST_EMAIL` / `TEST_PHONE` | |
| 12 | 2026-09-02 | One company, one row. Where several CIKs share a raise, that raise is counted in full for every CIK; the amount is not split and the run is not halted | |
| 13 | 2026-09-02 | Address gate reads the history JSON first and falls back to the XML filing. Measured: 168 of 2,937 companies have no history address and the filing covers all 168, so no missing-address reason code is created | |
| 14 | 2026-09-02 | `serviceable_countries` stores EDGAR's own two-character country codes, each looked up against EDGAR's published list rather than inferred | |
| 15 | 2026-09-02 | `mill_list` membership counts distinct companies, not occurrences. Measured: of 213 values occurring more than three times, 101 are one company's own address or phone, and excluding all 213 would strip both address and phone from 56 of 830 surviving companies | `appearing more than thrice in the data` |
| 16 | 2026-09-02 | `rolled_filing_count` joins the Clay payload, so a summed amount is never mistaken for a single raise. The column already exists on `outbound_companies_scored`; no schema change | |
| 17 | 2026-09-02 | The `contact_name` blanking rule is stated rather than assumed: the `authorizedRepresentative` flag, plus an agent vocabulary matched against `signatureTitle`, and a title naming a real office is kept. Measured 246 distinct titles, 20 agent-flavoured across 92 rows, and 21 rows flagged | |
| 18 | 2026-09-02 | `totalRemaining` is summed across the rolled filings like `totalAmountSold`, because it is an amount and the merge rule takes only non-amount fields from the newest filing | `the amount still left to raise in the round filed` |
| 19 | 2026-09-02 | Stated where a company already dealt with leaves the pipeline: re-entry on a fresh filing is by design, and customer, held, closed and lost are all removed on the dedupe join against the CRM-populated tables. No new reason codes, because those outcomes cannot fire at this build's volume | |
| 20 | 2026-09-02 | Four industry codes still carried the PDF's ampersands and could never match a filing: Hospitals, Airlines, Lodging and Tourism. EDGAR full-text search returns 0 Form D documents for each ampersand spelling against 153, 819, 365 and 1,232 for the `and` spelling, and no ampersand appears in any of the 3,571 rows pulled. Evidence in `docs/sources/edgar_industry_enum_spelling_2026-09-02.md`. **No withdrawn phrase**: those spellings are the PDF's own wording and legitimately live in the verbatim capture at `docs/sources/sec_form_d_official_2026-08-29.md`, so a text ban would fail on the evidence archive. The enforcement is the unmapped-code guard in `scripts/04_score.py`, which halts against live data and is what caught this | |
| 21 | 2026-09-02 | `people` stays JSON in Supabase and is flattened to one plain-text column on export to Clay. Clay receives clean, already-formatted data, and that is decided on formatting rather than on what a credit tier can afford | |
| 22 | 2026-09-02 | `website_from_edgar` measured across the full scored population instead of a 40-company sample: still 0, now 0 of 830, so Clay resolves every domain itself | `Measured 0/40 on operating companies` |
| 23 | 2026-09-02 | One human signing for more than three companies is collapsed to the highest-scoring one before Clay, the rest kept and pointed at it. Measured: 4 signers over 34 companies naming 7 humans between them, so per-company sending would be 60 emails to 7 people. New table `signer_list`, new code `dupe_same_signer` | |
| 24 | 2026-09-02 | Every address written to is recorded in `contacted_emails` and checked when Clay returns, so a person reached once is never reached again. New code `dupe_already_emailed` | |
| 25 | 2026-09-03 | Phones leave for Clay in one written format, E.164 for US numbers. Measured: 872 values arrived in five spellings, and the post-Clay dedupe compares phones as strings, so two spellings of one number would match nothing and report success. Non-US numbers keep their digits and get no country code guessed | |
| 26 | 2026-09-03 | A filing writing `N/A` in a name or phone box means there is no value, and it is dropped rather than shipped. It reached the payload as the phone to chase and as `N/A Lamar Advertising General Partner, LLC` in `people`, because a related person is often an entity and the surname box holds the company | |
| 27 | 2026-09-03 | The Clay payload is reordered into the order the work is done in, and `also_signed_for` moves beside `contact_name` because it is a fact about the signer. `website_from_edgar` is dropped from the payload: measured empty on all 830, it was 200 blank cells in a table a person reads. The column stays in Supabase | `Kept because it costs nothing and would save a credit if it ever fired` |
| 28 | 2026-09-03 | `people` excludes whoever is in `contact_name`, matched on first and last name with initials and honorifics dropped, so the two columns never repeat one human. Removed from 675 of 800 rows; 173 rows now have an empty `people`. Columns renamed for the destination: `current_name` singular, measured 799 of 800 single-valued, and `former_names` | |
| 29 | 2026-09-03 | Phones ship as digits only with the country code first and no plus sign, because a plus asserts a country code we can only verify for US numbers and would turn the one malformed value into a confident claim about the wrong country | `E.164 for US numbers` |
| 30 | 2026-09-03 | Block capitals are calmed per comma-separated segment, so acronyms inside mixed-case text survive. Measured: 20 fields keep a capitalised word and every one is a genuine acronym | |
| 31 | 2026-09-03 | Calming and phone formatting move from the export into `04_score.py`, so the payload table holds them and every consumer inherits them. n8n reads that table rather than the CSV, and the phone dedupe joins on it. Measured: 0 of 830 addresses left in capitals, against 662 before. Job-title acronyms added to the keep-uppercase list after 98 contacts read `Ceo` | `Block capitals are calmed on export` |
| 32 | 2026-09-03 | The copy rule invented in `CLAUDE.md` is deleted. Copy is governed only by **Enrichment and copy** in this document. `CLAUDE.md` holds process rules and no product facts, by its own opening line, and that bullet was a pipeline mechanism this document never states | `An LLM writes only the single relevance sentence` |
| 33 | 2026-09-04 | Copy is written by Claygent from a signal on the company's **own** site, paired with what that signal means for their money, and never from the funding round. The signal picks two Mercury features from a fixed list of five; the fifth is added at $250,000 and over of amount sold. Peer names are not cited: 38 of the 50 live rows are `Other Technology`, so the cluster's named customers failed the genuineness test far more often than they passed. The prompt is versioned at `prompts/claygent_copy.md` | `seeded competitor use cases` |
| 34 | 2026-09-04 | The CRM model is settled and built: Organization, Person and Deal; six stages; eleven custom fields. Nothing is superseded, because the original never named an object, a stage or a field. Verified against the live account by `scripts/09_pipedrive_probe.py` and archived at `docs/sources/pipedrive_fields_2026-09-04.md` | |
| 35 | 2026-09-04 | Domain comes from Claygent alone. The Find Work Email waterfall also emits one; on the 16 resolved rows the two disagreed five times and the waterfall was wrong every time, offering the filing agent's law firm, a data vendor or yahoo.com. It adds no coverage Claygent did not already have, so it is not read | |
| 36 | 2026-09-04 | The reply leg reads Gmail over OAuth, not IMAP. IMAP connected, reported no error, and returned nothing; its unread filter also fought the run, because opening the inbox to check whether mail had arrived marked it read and it stopped matching. Gmail's API answers a query and says why when it cannot | |
| 37 | 2026-09-04 | `v_funnel` rewritten and `v_outreach` added, in `db/migration_003_views.sql`. The old funnel counted 814 of the 830 scored companies nowhere, because it looked for a `not_selected` status no script writes, and it called 10 rows dispatchable on enrichment and dedupe alone when 5 of those had no copy to send | `every stage from ingest to
dispatchable` |

---

## Introduction

Mercury sells banking and finance operations to startups. This Go-to-Market Engineering build aims to
acquire new customers for Mercury by finding companies when they raise funding.

It is a cold email outreach system triggered by SEC Form D filings, where I did the data modelling and
edge case handling: schema design, ICP segmentation, scoring logic, priority scoring, and copy. Python
ingests and scores leads; Supabase is the truth layer; Clay for enrichment; n8n is the conveyor belt.

## The trigger

I got the idea to look at a funding event from Mercury's homepage, which declares 1 in 3 startups as
their customers, defining startups as entities reporting funding of Series A and below on Crunchbase
in the past year.

So, as Mercury's own definition of its market is companies that just raised, I needed the best
possible feed of that event, which is SEC Form D. Every US company that raises private capital files
one of these within fifteen days of its first sale. It's free, has a public API, and is formatted in
machine-readable XML.

### Why Form D

- **A relevant event**: a raise reopens the business banking question, the moment the pitch is relevant
- **Constant pipeline**: arrives every working day
- **Comprehensive dataset**: filing Form D is mandated by law for all eligible companies
- **Information density**: company name, industry, officers, address, and phone all non-optional
- **Free and machine-readable**: SEC EDGAR is a public REST API

### 10 rejected alternatives

| Source | Why not |
|---|---|
| SEC Form 1-A | A halfway house between a private raise and a stock market listing: the company sells shares to the general public. Few filings, and filing before the money arrives rather than after, so it is not a cash event. |
| 8-K, S-1, 10-Q | Public-company events. Those companies already have treasury desks and banking relationships. Wrong ICP entirely. |
| Crunchbase, PitchBook, Tracxn, Harmonic | Expensive and derivative: substantially built from Form D plus press, with a delay. |
| TechCrunch, Google News, Funding RSS | PR coverage skewing big and consumer. Amounts are often unclear, nobody is named, duplication of coverage across outlets. |
| Job postings / hiring spikes | Lags by months, carries no amount, and needs scraping. |
| Y Combinator / Techstars batches | Two batches a year gives no continuous pipeline. |
| State incorporation filings | Registering a company is not raising money. There is no cash and nothing to score. |
| LinkedIn headcount growth | Needs scraping. It also lags the raise and never tells you the amount. |
| USPTO trademark filings | Filing a trademark says little about whether a company just raised. |
| Product Hunt / launch feeds | Launching a product is not a money event. |

US incorporated companies which don't raise under Regulation D (crowdfunded, bootstrapped, and
revenue-financed companies) could be great candidates for Mercury, but an alternative pathway had to
be built to find them, which is out of scope for this build.

## Pulling and storing data

Python scripts use the REST endpoints from the EDGAR SEC database system to fetch:

1. The daily filing index, which has form type in the first column. This helps the system only pull
   Form Ds, which we need.
2. Each Form D of the day in XML.
3. Each company's filing history in JSON.

These raw documents get parsed into their constituent fields, one column per field, into two Supabase
tables:

- `filings_raw` for all filings with date, keyed on accession number plus CIK: a compound key as
  several companies can be listed in one filing if they sell in the same transaction.
- `entities_raw` keyed on CIK.

Both tables are upserted, so any re-run is safe and produces no duplicates. Storing every field of the
document rather than only the fields the model currently uses means a field ruled out today can be
refactored tomorrow if the scoring system changes, without a refetch of the documents.

Two things inside a filing repeat and cannot be a single column, so they get child tables joined on
`(accession_number, cik)`: `filing_related_persons` (median 2 people per filing, max 15) and
`filing_former_names`.

**One company, one row. Where several CIKs share a raise, that raise is counted in full for every
CIK.** The offering amounts are reported once for the whole filing and are not split between the
named issuers, so each co-issuer row carries the full `totalAmountSold`. Measured: 7 of 193 filings on
2026-08-27 name a co-issuer, 0 of 165 on 2026-08-20, and every one is a fund cut into legal vehicles
(a US and an offshore version of one fund, or a standard and a qualified-purchaser vehicle), so all of
them are routed out before scoring. An operating company raises as itself.

### Routing out funds

Form D is filed by funds as well as by operating companies, and this build only caters to companies.
So the next step is to separate out funds by looking at the values of 2 filing fields to catch all or
most of them:

- industry group set to `Pooled Investment Fund`, or
- the pooled-fund tick in the securities offered

Using either one of the two caused leaks. Measured across two full days: the union catches 120/193 and
103/165, and the tick alone catches 9 and 5 funds the industry group misses.

They move to a 3rd Supabase table `formd_funds` as Mercury advertises funds as one of their customer
segments. A separate flow can be built for them later as it requires different scoring logic and copy:
a fund's amount sold is committed capital drawn down over years, not cash sitting in an account.

### Routing out unserviceable companies

Mercury publishes exactly who it can serve: companies incorporated in the US, and physically located
in one of twelve countries (US, UK, Canada, India, Singapore, Israel, Netherlands, Spain, Germany,
Denmark, Australia or Mexico). These are both determined from the company's history as they are
required to be kept current by law with the SEC, and address on filings is sometimes that of an agency
or firm filing on the company's behalf.

Failing rows are routed out to the table `likely_unserviceable_companies`, which specifies if they
failed on jurisdiction or address (`jurisdiction_fail` and/or `address_fail`).

**The address is read from the company history first, and from the filing when the history has none.**
Measured on the 2,937 companies pulled: 168 have no business address in the history JSON, and the XML
filing supplies a state or country for **all 168**. So there is no null case and no reason code for a
missing address, which would be a code that can never fire. The history is preferred because a filing
address is sometimes the agent's; for those 168 the filing is the only source available, and that
residual risk is accepted rather than dropping the company.

**EDGAR writes countries as its own two-character codes**, not names: the data contains `E9`, `N4`,
`A1`, `A6`, `K3` and others. Each code is looked up against EDGAR's published list and the codes
themselves are stored in `serviceable_countries`. A code is never inferred from context.

### Parking companies with no scorable industry

A share of the remaining companies select `Other` as their industry group, which our scoring system
cannot use. Measured: 13 of 73 operating companies (18%) on 2026-08-27 and 15 of 62 (24%) on
2026-08-20. `industryGroupType` is never null; `Other` is a real checkbox on the form. EDGAR's `sic`
field is only 10% covered, so there is no free fallback.

In our system, as you will see, companies are scored first and then sent to Clay for enrichment and
copy drafting. In production, I'd send these companies to Clay for industry enrichment and have them
come back to Supabase for scoring. For now, they sit in a table `no_industry_companies`. Consider them
parked, not discarded.

Remaining companies go to `outbound_companies_unscored`.

## Scoring

The scoring model I designed for this demo is simple with 4 inputs, totaling 10 points up to 2 decimal
places, upon which a company's score is determined. Scoring parameters had to be taken from fields
which were reliably 100% coverage in the data.

| Input | Max | Source | Direction | Shape |
|---|---|---|---|---|
| Amount Sold | 5.00 | Form D | higher is better | log curve between Mercury's own form boundaries |
| Amount Remaining | 1.00 | Form D | lower is better | same curve inverted |
| Industry | 3.00 | Form D | ranked table match | seeded assumptions |
| Prior Form D filings | 1.00 | History | fewer is better | banded by test cases |

### Amount Sold, 5 points

```
Points = 5 x log10(1 + sold / 100_000) / log10(501), capped at 5.00
```

Count the raise in units of $100,000, take the log, and scale so $50M and above lands on 5. The +1 is
what lets a company that sold nothing score exactly zero.

| Raise in $ | Points |
|---|---|
| 0 | 0.00 |
| 50,000 | 0.33 |
| 100,000 | 0.56 |
| 250,000 | 1.01 |
| 1,000,000 | 1.93 |
| 10,000,000 | 3.71 |
| 25,000,000 | 4.44 |
| 50,000,000 | 5.00 |

Log, because three of the seller's four boundaries are powers of ten. Mercury's inbound form makes
every prospect pick from 5 expected balance bands bounded at $100k, $1m, $10m and $50m, and the first
three are 10^5, 10^6 and 10^7: each band ten times the last. A seller that widens its buckets by a
constant multiple is thinking about money logarithmically.

This is a proxy for the cash a company has on hand at the moment in time of the filing.

My first instinct was to let the data decide and let each day's filings set their own percentiles, but
company score will constantly shift and make the system hard to maintain.

### Multiple filings by one company

If a company is found to make 2 or more distinct filings within a rolling 12 months of `filingDate`,
anchored on the newest filing, before they become a customer, that number is added together in this
build. Dedupe on the fingerprint of the offering itself (`totalOfferingAmount`, `totalAmountSold`,
`dateOfFirstSale`, `totalNumberAlreadyInvested`) then add the amounts.

Both amounts are added: `totalAmountSold` and `totalRemaining`. Non-amount fields (industry, contact,
related persons, filing date) come from the newest filing.

**Adding filings up over 12 months never means a company already dealt with is emailed again.** A
company that files again re-enters the pipeline by design, because a fresh raise is a fresh trigger,
but whether it is still contactable is settled downstream, not here: the dedupe removes any row whose
apex domain matches `existing_mercury_customers` or `mercury_inbound`, flagged
`dupe_existing_customer` or `dupe_inbound` and counted in the funnel. **A company that becomes a
customer, or is held, closed or lost, is removed on that same join**, because in production those
tables are CRM-populated and carry every one of those outcomes. In this build they are the seeded
demo rows, so the held, closed and lost outcomes have no rows to fire on and get no reason code of
their own: a code that cannot occur at this volume is padding.

This is not an edge case. Measured on 2026-08-27: three CIKs filed more than one Form D that day, and
they were the large ones, Databricks at $241M and $5.00B. Nonlinear Materials filed five Form Ds on a
single day in 2025. Measured across the 20-day window: 113 of 830 surviving companies roll up more than
one filing, the largest being a note-issuing vehicle with 27.

### Total Remaining, 1 point

The same curve as amount, inverted:

```
curve(v) = log10(1 + v / 100_000) / log10(501), capped at 1
points   = 1 - curve(v)
```

| Remaining in $ | Points |
|---|---|
| 0 | 1.00 |
| 100,000 | 0.89 |
| 1,000,000 | 0.61 |
| 10,000,000 | 0.26 |
| 50,000,000+ | 0.00 |

One point goes to the amount still unsold across every filing rolled into the row, summed the same way
`totalAmountSold` is, and it exists to catch companies in the right industry that declared a large
offering and have sold none of it. Remaining is an amount, so it follows the merge rule that amounts
are added and only non-amount fields come from the newest filing. Reading only the newest filing would
let a company with $50M unsold across earlier rounds take the full point because its latest small
filing happened to close, which is the opposite of what the point measures. It also adds separation;
adding it leaves the model with materially fewer tie groups than amount sold produces on its own.

The assumption is that a company with most of its round closed is closer to making a banking decision.
It gets one point rather than more because its correlation with amount points is about +0.3 on test
cases, so it is a weaker second reading of something amount already measures rather than an
independent signal. Zero left to raise lands on exactly 1.00.

### Industry Match, 3 points

Source: https://www.sec.gov/files/formd.pdf

| Group | Code | Points |
|---|---|---|
| Technology | Other Technology | 3.00 |
| Technology | Computers | 3.00 |
| Health Care | Biotechnology | 2.70 |
| Health Care | Pharmaceuticals | 2.70 |
| Business Services | Business Services | 2.55 |
| Health Care | Other Health Care | 2.40 |
| Health Care | Health Insurance | 2.40 |
| Health Care | Hospitals and Physicians | 2.40 |
| Energy | Other Energy | 2.25 |
| Energy | Energy Conservation | 2.25 |
| Energy | Environmental Services | 2.25 |
| Energy | Electric Utilities | 2.25 |
| Technology | Telecommunications | 2.10 |
| Retailing | Retailing | 1.80 |
| Banking & Financial Services | Other Banking and Financial Services | 1.50 |
| Real Estate | Commercial | 1.20 |
| Real Estate | Residential | 1.20 |
| Real Estate | Construction | 1.20 |
| Real Estate | REITS and Finance | 1.20 |
| Real Estate | Other Real Estate | 1.20 |
| Manufacturing | Manufacturing | 0.90 |
| Agriculture | Agriculture | 0.90 |
| Restaurants | Restaurants | 0.90 |
| Travel | Airlines and Airports | 0.60 |
| Travel | Lodging and Conventions | 0.60 |
| Travel | Tourism and Travel Services | 0.60 |
| Travel | Other Travel | 0.60 |
| Energy | Oil and Gas | 0.30 |
| Energy | Coal Mining | 0.30 |
| Banking & Financial Services | Investing | 0.30 |
| Banking & Financial Services | Commercial Banking | 0.30 |
| Banking & Financial Services | Investment Banking | 0.30 |
| Banking & Financial Services | Insurance | 0.30 |

33 codes. The `Code` column is the exact XML enum value, which is why it reads `Oil and Gas` and
`REITS and Finance` and `Other Banking and Financial Services` rather than the PDF's ampersands. **No
code in this table uses an ampersand, and the check is EDGAR's rather than the form's.** Four of these
codes were seeded from the PDF and could never have matched a filing; `scripts/04_score.py` halted on
two of them the first time it met real data, which is what the unmapped-code guard exists for. EDGAR
full-text search over Form D returns **zero** documents for every ampersand spelling and 153, 819, 365
and 1,232 for the `and` spellings, and no ampersand appears in any of the 3,571 rows pulled. Captured in
`docs/sources/edgar_industry_enum_spelling_2026-09-02.md`.

The 34th code on the form, `Other`, is not scored: those companies are parked in
`no_industry_companies`. `Pooled Investment Fund` is routed out before scoring.

3 points to industry, for which I've created a seeded table of Mercury customers by lifetime value,
matched to the SEC's industry groups. A company belonging to an industry group which is Mercury's
highest-return group will score higher.

The clusters and the named Mercury customers per cluster live in `industry_clusters`, from the table
reproduced at `docs/industry_clusters.png`. The named customers were seeded to let the copy cite a
recognisable peer, and the copy does not use them: on the live 50 rows, 38 are `Other Technology`, so
the peer offered is almost always a company the prospect has no reason to feel kin to, and Claygent
was right to refuse it. The table stays as the industry map:

| Cluster | Form D codes | Named on Mercury's site |
|---|---|---|
| Technology | Other Technology, Computers, Telecommunications | Linear, Supabase, Sprig, Mona |
| Life Science | Biotechnology, Pharmaceuticals | Freedom Biosciences, TwoStep Therapeutics, Infinimmune |
| Healthcare Services | Other Health Care, Health Insurance, Hospitals and Physicians | Assort Health, Mochi Health |
| Business Services | Business Services | Ways & Means, Acuity, IBEX Consulting |
| Ecommerce | Retailing | Manta Sleep, Minaal, Raide |
| Climate | Other Energy, Energy Conservation, Environmental Services, Electric Utilities | Patch, Zeno Power, Renuble |
| Real Estate | Commercial, Residential, Construction, REITS and Finance, Other Real Estate | KindDesigns, Blue Maple Rentals |
| Crypto / Fintech | Other Banking and Financial Services | Phantom, CoinTracker, XMTP |

### Prior Form D Filings, 1 point

| Prior Filings | Points |
|---|---|
| 0 | 1.00 |
| 1 | 0.75 |
| 2 | 0.50 |
| 3 or 4 | 0.25 |
| 5 or more | 0.00 |

I've assumed the business banking questions would already have been settled with more filings, so more
filings score lower. Measured as a count of total Form Ds filed minus the number of Form Ds rolled
into the current row.

Another scoring factor I'll consider adding in prod: check internal data on the average conversion
time of companies by industry. This would help assign a time window per industry within which outreach
should be intensified, as the likelihood of conversion is higher. This would help further prioritise
leads and staff for this function.

### The Clay payload

Scored companies sit in `outbound_companies_scored` with date of filing, all scoring factors, the
final score, and the following parameters, ready to be sent to Clay for enrichment.

IDX = Filing Index, XML = Filing, JSON = Company History

**The column order is the order the work is done in**, because these columns are read left to right by
a person in a Clay table: the key and the priority, then who and what to search for, then the evidence
that confirms an answer, then the facts the copy is built from.

| # | Clay Row Name | Source | Purpose |
|---|---|---|---|
| 1 | `cik` | IDX | Company key |
| 2 | `score` | Scoring | Decides who is worked first, so it sits where it is read |
| 3 | `current_name` | XML entity name + JSON name, deduped to one if identical | Entry 1 to find brand names, website, emails. **Sent as `current_name`, singular**: measured 799 of 800 carry exactly one value, the sole exception differing only by entity suffix, `Kaleta Labs LLC` against `Kaleta Labs, Inc.` |
| 4 | `former_names` | XML issuer previous name + XML EDGAR previous name + JSON former names, deduped | Entry 2. Load-bearing where a legal name is opaque: `CSS Solutions LLC` files under the former name `Charlie Sierra Sierra LLC` |
| 5 | `contact_name` | XML signer plus title. Blank if attorney or authorised person/representative, by the rule below | The person to find, and the strongest evidence that a domain is the right one |
| 6 | `also_signed_for` | Signer collapse | The other companies this same person signed for. It sits beside `contact_name` because it is a fact about that person, not about this company |
| 7 | `people` | XML related persons first name + last name + relationship, **excluding whoever is in `contact_name`** | More humans to find, and to corroborate a domain. Officers may be contacted, directors and promoters never are |
| 8 | `address_candidates` | XML issuer street, city, state, zipcode + JSON street, city, state, country, zipcode. Deduped against `mill_list`. Strip punctuation, expand street types, map state to 2-letter code | **Corroboration only.** Confirms a domain, never disqualifies one |
| 9 | `phone_candidates` | XML issuer phone number and JSON phone, digits only with the country code first. Deduped on `mill_list`. Keep both if different | **Corroboration only**, on the same terms |
| 10 | `industry` | XML industry group type | |
| 11 | `amount_sold` | XML | |
| 12 | `amount_remaining` | XML | |
| 13 | `rolled_filing_count` | Rollup | **How many Form D filings were added together to produce `amount_sold`.** 1 for most companies. Measured: 113 of 830 roll up more than one filing, and the largest is a note-issuing vehicle with 27 in twelve months. Without it, a summed figure is indistinguishable from a single raise, and copy generated from the row could describe twenty-seven issuances as one round |
| 14 | `prior_formd_count` | JSON recent Form D filings counted | |
| 15 | `filing_date` | IDX | |

**`website_from_edgar` is not sent.** The column stays on `outbound_companies_scored`, because storing
it costs nothing and a future pull may find EDGAR populating it, but it is measured empty on **0 of all
830 scored companies** and shipping 200 blank cells to Clay is noise in a table a person has to read.
`investorWebsite` is never sent either: it is an investor-relations URL, not the company domain.

**`people` never repeats `contact_name`.** The signer and the related-persons list are separate boxes
on the form, so the same human is typed differently in each: `Sagar Kadakia` against `SAGAR KADAKIA`,
`Christopher M. Kane` against `Christopher Michael Kane`, `Sheila Gujrathi, M.D.` against
`Sheila Gujrathi`. Matching is on **first and last name, lowercased, with honorifics and single-letter
initials dropped**, which collapses all three pairs. Measured: the contact was removed from 675 of 800
rows, and 173 rows are left with an empty `people` because the contact was the only human named, which
is the truth about those filings rather than a loss.

**Two names that share a surname are not merged.** 45 rows still carry someone with the contact's
surname and nearly all are genuinely different people, because at this stage a co-founder or a spouse
is common: Petfolk names Audrey and Michael Wystrach, EarthGrid names Troy and Alysia Helming. Fuzzy
matching would catch the two real duplicates that remain, a typo in `Keven` against `Kevin A. Strauss`
and a middle-name alias in `Alex Wylie` against `James Alexander Wylie`, and would also merge the
Wystrachs. The exact rule is kept and the residual is stated.

**The dedupe only applies when the signer is our contact.** Where `contact_name` was blanked as an
agent, `people` stays complete, because it is then the only place a human is named at all.

**`contact_name` is blanked when the signer is not the company's own officer**, on two tests. The
filing's `authorizedRepresentative` flag being true blanks it outright, measured on 21 of 1,103
surviving filing rows. Otherwise the free-text `signatureTitle` is matched against the agent
vocabulary: attorney, attorney-in-fact, power of attorney, authorised person, authorised
representative, authorised signatory, authorised signer, filing agent, registered agent.

**A title that names a real office before any agent wording keeps its name**, because the agent words
appear inside genuine officer titles: `chief executive officer, duly authorized` is a CEO, and blanking
it would throw away exactly the human the payload exists to find. **Whichever comes first in the title
decides**, which is what separates that CEO from `power of attorney for samuel seeton, president`,
where the office belongs to the person being signed for rather than to the signer. Measured:
`signatureTitle` is free text with 246 distinct values across the surviving rows, of which 20 are
agent-flavoured and cover 92 rows. Every row carries a signer, so this never fires on a missing name:
0 of 1,103 rows have none.

**A value a filing uses to mean nothing is dropped, never shipped.** `N/A` in the phone box is not a
phone, and a related person is frequently an entity rather than a human, so the first and middle name
boxes carry `N/A` and the surname box carries the company. Joined naively that reaches Clay as
`N/A Lamar Advertising General Partner, LLC` and as `Andrew n/a Millard`. Both are cleaned where the
candidate is built, not on the way out, so the payload table itself is clean.

**Phones leave in one written format: digits only, country code first, nothing else.** Measured: 872
phone values arrived in five spellings of the same thing, `650-549-1400`, `(650) 549-1400`,
`6505491400`, `650.549.1400` and worse. Claygent reads them alike, but the dedupe after Clay compares
phones as strings, and two spellings of one number match nothing while reporting success, which means
emailing a customer we already have. A US number gains its leading 1 so it has the same shape as the
rest.

**There is no plus sign, and that is deliberate rather than untidy.** A plus asserts that the digits
after it are a real country code, which is only knowable for the US numbers here. `44 7835 097 128` is
a genuine UK number and `757-434-25343` is a typo, and prefixing both would turn the typo into a
confident claim about Russia. Digits alone assert nothing, compare exactly, and a dialler can add the
plus once a country is established. Measured on the export: 854 values, 842 US, 12 non-US or
malformed and left exactly as their digits.

**Block capitals are calmed when the payload row is built.** Many filers type in caps lock, and `SAGAR KADAKIA` and
`1 LIBERTY STREET` read worse than `Sagar Kadakia` and `1 Liberty Street`, besides making a name look
like an acronym. This is applied per comma-separated **segment**, never per field or per word, so a
real acronym inside ordinary text survives: `FSH Technologies`, `EXUMA Biotech` and `AURA Network
Systems` keep their capitals because those segments are mixed case, while `NEW YORK` sitting beside a
title-cased street does not. Within a calmed segment, a token holding a digit, a legal suffix or a
state code is left alone, so `DS1`, `LLC` and `NY` stay as filed, along with the job-title acronyms:
without `CEO` on that list, 98 contacts read `Ceo`.

**Both this and the phone format are applied in `04_score.py`, not on export, so every consumer
inherits them.** n8n reads `outbound_companies_scored` rather than the CSV, and outbound facts are
substituted straight from the row, so a value left shouting in the table would be shouted in the email
and written into the CRM. The phone case is stronger still: the dedupe after Clay compares phones as
strings against the customer tables, so a raw phone stored here would fail that join silently.
`filings_raw` keeps the filing's own text untouched, so provenance survives one table down and nothing
is lost. Measured after the move: 0 of 830 addresses remain in block capitals, against 662 before.

**`people` is stored as JSON and sent to Clay as one plain-text column.** Supabase keeps it structured
because the truth layer is SQL and a question like how many companies name a CFO on the filing is a
query against structure, not a substring hunt through a sentence. Clay is a different consumer: it
receives a CSV, a JSON blob in a cell would have to be parsed inside a Clay formula, and no column
Clay runs an action on should need unpacking first. So the export flattens it to
`Jane Doe (Executive Officer); John Roe (Director, Promoter)`, one row per company, and the primary
target continues to travel separately as `contact_name`, already a plain string. **The rule is that
Clay receives clean, already-formatted data**, and it does not bend for what a credit tier can afford.

`mill_list` stores addresses and phone numbers of agencies and mills filing on behalf of companies, so
that the right candidate addresses and phone numbers can be sent to Clay.

## One person, one email

**A person is written to once. Not once per company they signed for.**

One human signs Form D for many companies, and those companies are one operation wearing several
names. Measured across the 830 scored: Rezwan Manji signs for 19, Alfonso Cahero for 7, Christopher
Kane for 4, Tadd Miller for 4. **Those 34 companies name 7 distinct humans between them.** Cahero's
seven name the identical pair every time; Kane's four name only him. Sending per company would be 60
emails to 7 people. Corroborated independently by `mill_list`: 16 of Manji's 19 companies, and all of
Cahero's and Kane's, had already lost their address for being shared by more than three companies.

Two guards do this, at different stages and on different evidence.

**Before Clay, the signer collapse.** `signer_list` counts how many distinct companies each signer
covers, built exactly as `mill_list` is and for the same reason: it is a table, not a per-run check,
because a signer who appears four times this month appears again in March and must be caught on the
next pull too. The signer name is normalised before counting, because `Tadd M. Miller` and
`Tadd Miller` are one human filed two ways. **Above three companies, only the highest-scoring company
goes to Clay.** The rest stay in `outbound_companies_scored` marked `dupe_same_signer`, carrying
`collapsed_into_cik` so any removal can be opened and checked. The kept row carries `also_signed_for`,
the sibling company names, so nothing is lost and the copy knows it is writing to someone running
several entities. Measured: 30 of 830 routed out, 4 kept.

**Three is allowed through on purpose**, and the cost is stated rather than hidden: 30 signers over 70
companies, up to 40 extra emails. Those are caught downstream instead, on better evidence.

**After Clay, the address check.** Every address ever written to is recorded in `contacted_emails`,
keyed on the address rather than the company, because the thing being protected is a person's inbox
and it must outlive the run, the company and the campaign. It is checked in the same pass as the
existing-customer and inbound joins, and a match exits `dupe_already_emailed`. This is what makes the
threshold of three safe: three companies from one desk usually resolve to one address, and the second
and third are stopped here.

**Nothing real is ever written to this table in this build**, because only seeded test rows are
sendable. To prove the check fires, rows are seeded into it marked `is_demo_seed` after Clay returns
real addresses, and seeded rows are excluded from reported counts. The same method the demo uses for
the customer tables, and it fabricates nothing upstream of the match.

**A value is an agency's only when more than three distinct companies use it.** Membership is counted
on distinct CIK, never on how often the value appears, because those two counts mean opposite things.
Measured on the 3,571 filing rows: 213 values appear more than three times, but **101 of them belong to
a single company** filing repeatedly from its own premises, the largest being a head office appearing
74 times for one CIK. Excluding all 213 would send **56 of the 830 surviving companies** to Clay with
neither an address nor a phone, removing two of the four entries that resolve a domain. Counting
distinct companies instead keeps every real agent: one phone shared by 238 companies, a Lynnwood
address by 194, a Claymont address by 193, a Dover address by 70.

`occurrence_count` is still recorded next to `distinct_cik_count`, because the pair is what separates a
shared filing agent from a company that simply files often.

## Enrichment and copy

Clay resolves each surviving company to a domain, a work email, and the copy.

The domain and the copy are Claygent; the email is Clay's native Find Work Email waterfall, which
includes validation. `contact_name` is split to a first-name-only column before it reaches the
waterfall, because the scored table stores it as `Name, Title` and the waterfall reads it as a full
name. Where `contact_name` is empty, the first person in `people` whose roles include
`Executive Officer` is used instead; a row with neither routes out.

Copy opens on one signal read off the company's **own** site, paired in the same sentence with what
that signal means for their money. The funding round is never mentioned: every email in the campaign
would otherwise open the same way. Claygent takes the first of seven signals it finds, in this order:
multiple sites or locations, named enterprise customers, open roles, operations outside the US, a
pricing page, hardware or inventory or freight, contractors or franchisees. Finding none is a normal
outcome and the email opens on the features instead.

The signal then picks two of five Mercury benefits, so the benefit answers the thing observed rather
than being chosen at random. Amount sold is the expected balance and bands the rest: at $250,000 and
over a third benefit is added, Mercury Treasury; at $10M and over the email offers a named
relationship manager. Every row, at every band, gets the demo link. No yield figure is ever quoted,
because Mercury's headline rate is its ceiling for balances over $20M and does not describe a
$300,000 prospect.

The prompt is versioned at `prompts/claygent_copy.md` and is the authority on its own wording.

### What Clay actually returned

Measured 2026-09-04 on the 50 rows sent, by `scripts/07_import_clay_results.py`:

| | Rows |
|---|---|
| Domain resolved | 16 |
| Validated work email | 13 |
| Copy written | 8 |

The eight with copy are the demo set. The 34 rows with nothing back are left `pending`, not
`enrich_no_domain`: the free tier ran out before Clay reached them, and calling an unreached row a
resolution failure would claim a measurement that was never taken.

**The domain is Claygent's, not the waterfall's.** Find Work Email emits a domain of its own, and
where the two disagreed, on five of the sixteen, the waterfall was wrong every time: it offered
`polsinelli.com` for Tabnam, which is the law firm that filed for them, `preqin.com` for Gnau, which
is a data vendor, and `yahoo.com` for Libertystream. Claygent resolved all sixteen unaided, so the
waterfall's domain adds no coverage and only offers filing agents.

`contact_name` is rewritten on import from Clay's split column and the title it dropped lands in
`contact_title`, which is where it should have been written in the first place.

Rows Clay cannot resolve do not disappear. They are flagged `enrich_no_domain` or
`enrich_no_work_email` and counted in the funnel. Contactability is settled here, upstream of the
sender: a row only becomes dispatchable when it has a verified email.

## Deduping against inbound and existing customers

We have to consider that Mercury has an inbound system as well as a large group of existing customers.
Those reside on `existing_mercury_customers` and `mercury_inbound` on Supabase and for the demo have
been seeded and already enriched with the required fields.

The dedupe runs **after Clay has returned**, because it joins on domain and domain only exists once
Clay has resolved it. Both checks are joins in SQL, on normalised apex domain, with phone as a
secondary check. Neither table carries a CIK: it is not needed, and a real Mercury customer list would
not have one. Removals are flagged `dupe_existing_customer` or `dupe_inbound` and counted.

### The demo seeds

The three dedupe targets start empty, so the codes cannot fire and their rates would be guesses. Run
by `scripts/08_dedupe.py --seed`, from the eight rows that have copy, so each code is measured against
a candidate that was otherwise going out:

| Seed | Table | Fires |
|---|---|---|
| `atoms.co` | `existing_mercury_customers` | `dupe_existing_customer` |
| `qualitate.io` | `mercury_inbound` | `dupe_inbound` |
| `delphiinteractive.com` | `contacted_emails` | `dupe_already_emailed` |

Each fired on exactly one row. The rate is recorded in `reason_codes` as seeded rather than natural,
because at eight companies a genuine collision would not occur and reporting one would be a lie.

`coderabbit.ai` and `blacksmith.sh` become the test rows, their addresses replaced by `TEST_EMAIL`.
The replacement is destructive on purpose: a real address kept beside a test flag is an address that
can still be sent to.

That leaves **five dispatchable rows**: two test rows that send, and three real companies that stop
at Enriched with a drafted email and a task.

Only after the dedupe does n8n fill the CRM and send the emails to test rows.

## Flywheel and CRM

n8n takes the enriched companies and logs all of them to Pipedrive. It sends only to the seeded test
rows, catches the reply, and moves the deal's pipeline stage in Pipedrive to match.

### The three workflows

**1, outbound run.** Reads the dispatchable rows, creates the Organization, Person and Deal, writes
all three ids back, then branches. A test row is emailed and its deal moves to Emailed; a real company
gets a Pipedrive task holding the drafted subject and body, and its deal stays at Enriched.

**2, reply catcher.** Reads Gmail, matches the sender against `work_email` on a row already at
`crm_stage` emailed, moves that deal to Replied and stamps `replied_at`. A reply from an address we
never wrote to matches nothing and ends quietly, which is a normal thing to receive.

**3, flywheel.** Won deals are written into `existing_mercury_customers`, so the next Form D from that
company is deduped out instead of emailed. This is what makes the dedupe self-feeding rather than
seeded.

### Idempotency is a query, not a lookup

Workflow 1 asks Supabase only for rows whose `pipedrive_deal_id` is still null. A row already in the
CRM is never fetched, so re-running cannot produce a second deal and no find-or-create search is
needed. The ids are written back the moment each object exists, so a run that dies halfway resumes.

### The compliance rule is a node that fails the run

Not an `if` that skips. A row flagged `is_test_row` whose address is not in `TEST_EMAILS` stops the
workflow with an error, because a rule enforced by convention is a rule that eventually sends to a
real company.

Each test row has **its own** inbox. One shared address cannot demonstrate a reply: the sender is what
ties a reply back to a row, and two rows on one address make that match ambiguous. The real address is
replaced rather than kept beside the flag, because an address still sitting in the row is an address
that can still be sent to.

### Gmail, not IMAP

Reply catching reads the Gmail API over OAuth. IMAP was tried first and is the wrong tool here: it
connected, reported no error, and returned nothing, and its unread filter fought the run, because
opening the inbox to check whether a message had arrived marked it read and it stopped matching. Read
unfiltered it pulled every unread message in a personal mailbox and took the process to a 2 GB heap.
The Gmail query is scoped to the test inboxes, so nothing else is fetched at all.

There is no webhook anywhere. A self-hosted webhook needs a public URL, and a tunnel gets a new
address on every restart, so the workflow would break each time n8n stopped.

### Measured, 2026-09-04

| | |
|---|---|
| Deals created | 5 |
| Emailed | 2, both test rows |
| Real companies emailed | **0** |
| Real companies at Enriched with a drafted task | 3 |
| Deals moved to Replied by a real reply | 2 |

Every one of the five carries its Organization, Person and Deal id in Supabase.

### The objects

Three, which is Pipedrive's native shape: **Organization** is the company, **Person** is the human
who gets the email, **Deal** is the raise. The split is what makes a second raise cheap: a company
that files again is matched to its existing Organization on domain and its existing Person on email,
and gains a second Deal. Duplicating the company was the alternative, and the dedupe joins on domain,
so a duplicate Organization would be a duplicate of the thing the dedupe reads.

A field lives on the object it describes and that outlives the Deal. CIK, domain and industry belong
to the company and never change; the score, the amount, the filing date and the written email belong
to that one raise. Company name, person name and person email are Pipedrive's own built-in fields
rather than custom ones, because the built-in email field is what Pipedrive matches an inbound reply
against.

### The stages

`Enriched`, `Emailed`, `Replied`, `Held`, `Closed Won`, `Closed Lost`. Every Deal is created at
Enriched, meaning it has a validated work email and written copy.

Only a seeded test row ever reaches Emailed. A real company's Deal stays at Enriched with the drafted
subject and body attached, which puts the compliance rule on the board instead of leaving it as an
absence. Closed Won and Closed Lost are stages **and** flip Pipedrive's native won/lost flag, so the
end of the pipeline is visible in the pipeline view rather than only in a report.

`Held`, `Closed Won` and `Closed Lost` are set by the person working the deal, not by the pipeline.
That is not a review queue: a rep working a live reply is the job, and Closed Won is where
`existing_mercury_customers` gets filled in production, which is what closes the flywheel.

### Ownership

Supabase owns the state and Pipedrive mirrors it, as everywhere else in this build. n8n writes each
Pipedrive id back into `outbound_companies_scored` the moment that object exists, so a run that dies
halfway resumes instead of creating a second set of objects.

Pipedrive addresses a custom field by a forty-character key, never by its display name. That map is
archived at `docs/sources/pipedrive_fields_2026-09-04.md`, fetched by `scripts/09_pipedrive_probe.py`.

Pipedrive has no free tier: this runs inside the fourteen-day trial, which takes no card, and no card
is ever added. Budget stays $0 and the CRM leg is time-boxed rather than free forever.

## Reporting

Replies are logged back into Supabase, and campaign health is read from SQL views sitting on those
same tables: `v_funnel` for the pipeline, `v_outreach` for the CRM leg. There is no unit-economics
view, because spend is $0 and there is no cost table; one would report zeros and imply a measurement.

### v_funnel

Every stage from ingest to an email that could actually be sent, with each stage as a percentage of
ingested. Measured 2026-09-04:

| Stage | Reason | Companies | % of ingested |
|---|---|---|---|
| ingested | | 3,512 | 100 |
| routed_out | `scope_pooled_investment_fund` | 1,996 | 56.83 |
| routed_out | `scope_non_us_incorporation` | 232 | 6.61 |
| routed_out | `scope_unsupported_country` | 106 | 3.02 |
| parked | `scope_industry_other` | 346 | 9.85 |
| scored | | 830 | 23.63 |
| held_back | `dupe_same_signer` | 30 | 0.85 |
| never_sent_to_clay | `free_tier_row_cap` | 784 | |
| enrich_failed | `enrich_no_work_email` | 3 | 0.09 |
| enriched | | 13 | 0.37 |
| removed | the three dedupe codes | 1 each | |
| has_copy | | 5 | 0.14 |

The stages after `scored` add to 830 exactly: 30 + 784 + 3 + 13.

Two stages are named for what happened rather than for a status. **`never_sent_to_clay` is a budget
boundary, not a resolution failure**: 780 companies never fitted the free tier and 34 were sent but
Clay ran out of credits first. Calling them `enrich_no_domain` would claim a measurement nobody took.
**`has_copy` replaces dispatchable**, because enrichment and dedupe alone say a row has an address,
not that there is anything to send to it.

`never_sent_to_clay` excludes the same-signer rows, which are also `pending`. Counting every pending
row put them in two stages at once and the funnel added to 860 against 830 scored.

### v_outreach

One row per CRM stage, splitting test rows from real companies and counting sends and replies.
Measured 2026-09-04:

| Stage | Deals | Test | Real | Sent | Replied |
|---|---|---|---|---|---|
| enriched | 3 | 0 | 3 | 0 | 0 |
| replied | 2 | 2 | 0 | 2 | 2 |

This is the compliance rule made readable in SQL rather than asserted in prose. Real companies sit at
`enriched` with `sent = 0`. A real company with `sent > 0` would be one visible line.

### What this build cannot report

Reply rate, open rate, deliverability, cost per lead, the domain resolution rate, and the natural
dedupe rates. The replies are the build's own test emails; there is no tracking, by design, because a
pixel or a redirect domain is what harms deliverability; there is no cost table and nothing was paid
for; 16 of 50 domains is where the free tier stopped; and all three dedupe codes fired against seeds.
A view that reported any of them would be reporting a number nobody measured.

***

In production, the EDGAR pull runs on a cron. Later, layer on cold calling and email sequences.
