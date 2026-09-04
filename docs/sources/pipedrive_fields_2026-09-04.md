# Pipedrive field map

Fetched 2026-09-04 by `scripts/09_pipedrive_probe.py`.
Pipedrive addresses a custom field by its 40-character key, never by its
display name. This is that map, and it is what the n8n step writes to.

## organization

| Field | Type | API key |
|---|---|---|
| CIK | varchar | `1f4ef25c25e14c1351d84030753e555b7f019c4b` |
| Domain | varchar | `f74ce5e0ca0db0f38abe652c19a5a6013e42f6ba` |
| Industry | varchar | `7302cd1183bc0878726d053b9433c6a776b67bdf` |

## person

| Field | Type | API key |
|---|---|---|
| Job Title | varchar | `d879fcf316034a9607ea9c0dbba289822d0c44a9` |

## deal

| Field | Type | API key |
|---|---|---|
| Email Body | text | `fb5b67596d7a50ab7a36fa4431a6ed86eb768394` |
| Email Subject | text | `209ff0beed324ebc4951a62a09ce389b2f6f53d8` |
| Filing Date | date | `cdcd3b138e0bd1897967da5402993eda7d061e86` |
| Held Until | date | `e8aaf315c015b1e5f04a88d9086c1f3a5c1ce04b` |
| Observation URL | text | `50af5fa7ac87a6e45286b13f88379428dad798d6` |
| Score | double | `6bce248051120fe8897a8025d4d024517114e34d` |
| Site Signal | text | `037a257f251c913cefa6cf1b01f05da8840bf0ec` |

## Stages

| Pipeline | # | Stage | stage_id |
|---|---|---|---|
| Form D Outbound | 0 | Enriched | 1 |
| Form D Outbound | 1 | Emailed | 6 |
| Form D Outbound | 2 | Replied | 2 |
| Form D Outbound | 3 | Held | 3 |
| Form D Outbound | 4 | Closed Won | 7 |
| Form D Outbound | 5 | Closed Lost | 8 |
