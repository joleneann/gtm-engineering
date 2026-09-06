# Pipedrive field map

Fetched 2026-09-04 by `scripts/09_pipedrive_probe.py`.
Pipedrive addresses a custom field by its 40-character key, never by its
display name. This is that map, and it is what the n8n step writes to.

The first three columns of each table are quoted: they are what the probe
returned. **Filled from** is derived, read out of `n8n/wf1_outbound_run.json`
on 2026-09-06. Every value comes from one column of `outbound_companies_scored`,
because that one table is all the workflow reads.

## organization

| Field | Type | API key | Filled from |
|---|---|---|---|
| CIK | varchar | `1f4ef25c25e14c1351d84030753e555b7f019c4b` | `cik`, cast to text |
| Domain | varchar | `f74ce5e0ca0db0f38abe652c19a5a6013e42f6ba` | `domain` |
| Industry | varchar | `7302cd1183bc0878726d053b9433c6a776b67bdf` | `industry` |

The Organization's own name is the first entry of `current_name_candidates`.

## person

| Field | Type | API key | Filled from |
|---|---|---|---|
| Job Title | varchar | `d879fcf316034a9607ea9c0dbba289822d0c44a9` | `contact_title` |

The Person's name is `contact_name` and the primary email, labelled work, is
`work_email`.

## deal

| Field | Type | API key | Filled from |
|---|---|---|---|
| Email Body | text | `fb5b67596d7a50ab7a36fa4431a6ed86eb768394` | `copy_body` |
| Email Subject | text | `209ff0beed324ebc4951a62a09ce389b2f6f53d8` | `subject` |
| Filing Date | date | `cdcd3b138e0bd1897967da5402993eda7d061e86` | `filing_date` |
| Held Until | date | `e8aaf315c015b1e5f04a88d9086c1f3a5c1ce04b` | nothing writes it |
| Observation URL | text | `50af5fa7ac87a6e45286b13f88379428dad798d6` | `copy_observation` |
| Score | double | `6bce248051120fe8897a8025d4d024517114e34d` | `score` |
| Site Signal | text | `037a257f251c913cefa6cf1b01f05da8840bf0ec` | `copy_signal` |

The Deal's title is the company name and its filing date, and its value is
`amount_sold` in USD. Every Deal is created in pipeline 1 at stage 1.

Held Until is the one field no workflow touches. A Deal only reaches Held when
a person parks it there, so the date they are waiting on is theirs to enter.

## Stages

| Pipeline | # | Stage | stage_id |
|---|---|---|---|
| Form D Outbound | 0 | Enriched | 1 |
| Form D Outbound | 1 | Emailed | 6 |
| Form D Outbound | 2 | Replied | 2 |
| Form D Outbound | 3 | Held | 3 |
| Form D Outbound | 4 | Closed Won | 7 |
| Form D Outbound | 5 | Closed Lost | 8 |
