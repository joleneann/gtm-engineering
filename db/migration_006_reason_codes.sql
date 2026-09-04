-- Migration 006: make reason_codes describe what actually happened.
--
-- PROPOSED. Not applied. Apply through the Supabase SQL editor.
--
-- Three things are wrong with the seeded table, all of them staleness rather
-- than design:
--
-- 1. `not_selected` is a code no script writes. It described a cutoff that was
--    never built: rows did not lose a Clay slot on score, the free tier simply
--    ran out. v_funnel reports that population as `free_tier_row_cap`, which is
--    not in this table at all, so the funnel names a code the code list does
--    not have and the code list names one nothing can reach. CLAUDE.md: a code
--    for a condition that cannot occur is padding.
--
-- 2. Four measured_rate values are still the 40-company sample taken before the
--    full pull existed. The real figures are in v_funnel over all 3,512.
--
-- 3. Three say "unmeasured until Clay runs". Clay has run.
--
-- No DDL. No column, table or constraint changes. This is an update to seeded
-- reference data, and every figure below is read from v_funnel on 2026-09-04.
--
-- Revert: db/revert_006.sql restores the previous eleven rows exactly.

begin;

-- Reachable, and it is where 784 of the 830 scored companies stopped.
insert into reason_codes (code, stage, exits_to_table, description, measured_rate, seq) values
 ('free_tier_row_cap', 'enrich', null,
  'Never sent to Clay. 780 did not fit the 200-row free table and 34 were sent but the credits ran out first. A budget boundary, not a failed enrichment.',
  '784 of 830 scored, 22.32% of ingested', 5)
on conflict (code) do update
   set stage = excluded.stage,
       exits_to_table = excluded.exits_to_table,
       description = excluded.description,
       measured_rate = excluded.measured_rate,
       seq = excluded.seq;

-- No row anywhere carries it, and nothing writes it. Checked against the live
-- database before writing this: enrichment_status holds only pending,
-- enrich_no_work_email and enriched.
delete from reason_codes where code = 'not_selected';

-- The sampled rates, replaced by the full population.
update reason_codes set measured_rate = '1,996 filings, 56.83% of ingested'
 where code = 'scope_pooled_investment_fund';
update reason_codes set measured_rate = '232 companies, 6.61% of ingested'
 where code = 'scope_non_us_incorporation';
update reason_codes set measured_rate = '106 companies, 3.02% of ingested'
 where code = 'scope_unsupported_country';
update reason_codes set measured_rate = '346 companies, 9.85% of ingested'
 where code = 'scope_industry_other';

-- Clay has run. A measured zero is a result; "unmeasured" is not.
update reason_codes
   set measured_rate = '0 of the 16 companies Clay reached'
 where code = 'enrich_no_domain';
update reason_codes
   set measured_rate = '3 of the 16 companies Clay reached'
 where code = 'enrich_no_work_email';
update reason_codes
   set measured_rate = '1 row, against a seeded address. Never measured naturally at this volume'
 where code = 'dupe_already_emailed';
update reason_codes
   set measured_rate = '1 row, against a seeded customer. Never measured naturally at this volume'
 where code = 'dupe_existing_customer';
update reason_codes
   set measured_rate = '1 row, against a seeded inbound company. Never measured naturally at this volume'
 where code = 'dupe_inbound';

commit;

-- Verification: ten codes, none unmeasured, and every code v_funnel names is here.
--
--   select code, seq, measured_rate from reason_codes order by seq;
--
--   select distinct f.reason_code
--     from v_funnel f
--    where f.reason_code is not null
--      and f.reason_code not in (select code from reason_codes);
--   -- expects zero rows
