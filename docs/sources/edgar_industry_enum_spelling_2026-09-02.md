# Form D `industryGroupType`: ampersand or "and", settled against EDGAR

Fetched 2026-09-02. Public, free, no key.

## Why this capture exists

`docs/sources/sec_form_d_official_2026-08-29.md` is a capture of the Form D **PDF**, and the PDF prints
these industry groups with ampersands. **The XML enum does not use them.** The scoring table in
`docs/source_of_truth.md` was seeded partly from the PDF, so four of its 33 codes could never match a
filing, and `scripts/04_score.py` halted on two of them the first time it ran against real data.

The PDF cannot settle the question, because it is not what the filings carry. This is EDGAR answering
it directly.

## Method

EDGAR full-text search, restricted to Form D, one query per spelling. A spelling the XML never uses
returns zero documents.

```
https://efts.sec.gov/LATEST/search-index?q="<phrase>"&forms=D
```

Run with the project's `SEC_USER_AGENT`, 0.3s between requests. The full script is
`scratchpad/check_enum_spelling.py` as run on 2026-09-02.

## Result, verbatim document counts

| Ampersand spelling | Hits | "and" spelling | Hits |
|---|---|---|---|
| `Airlines & Airports` | **0** | `Airlines and Airports` | **153** |
| `Lodging & Conventions` | **0** | `Lodging and Conventions` | **819** |
| `Tourism & Travel Services` | **0** | `Tourism and Travel Services` | **365** |
| `Hospitals & Physicians` | **0** | `Hospitals and Physicians` | **1,232** |
| `Oil & Gas` | 24 | `Oil and Gas` | 10,000 (capped) |

## Reading

Every ampersand form returns **zero** Form D documents. The `Oil & Gas` row is the control and its 24
hits are company names containing the string, not the enum, which is why the source of truth already
carried `Oil and Gas` correctly.

Corroborated independently by the pull itself: across **3,571 filing rows** in `filings_raw`, spanning
29 distinct `industryGroupType` values, **not one contains an ampersand**, and both
`Hospitals and Physicians` and `Lodging and Conventions` appear.

## Consequence

Four codes in `industry_scores` were corrected from the PDF's spelling to the XML's:
`Airlines and Airports`, `Lodging and Conventions`, `Tourism and Travel Services`,
`Hospitals and Physicians`. Applied by `db/fix_004_industry_codes.sql`. Source of truth changelog 20.
