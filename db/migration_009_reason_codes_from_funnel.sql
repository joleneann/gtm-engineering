-- Migration 009: make reason_codes agree with v_funnel again.
--
-- Apply through the Supabase SQL editor. No DDL. No table, column or
-- constraint is touched. This is seeded reference data only.
--
-- WHAT IS WRONG
--
-- Migration 006 set every measured rate from the funnel as it stood on
-- 2026-09-04. Migrations 007 and 008 then rebuilt that funnel: it counts
-- companies rather than filings, counts each company once at the furthest gate
-- it reached, and its denominator became the 2,953 distinct CIKs in
-- filings_raw rather than 3,512 filings. The rates in this table were never
-- re-read, so five of them now name figures the funnel contradicts:
--
--   code                          reason_codes says      v_funnel says
--   scope_pooled_investment_fund  1,996 filings 56.83%   1,664 companies 56.35%
--   scope_non_us_incorporation    232 companies 6.61%    232 companies 7.86%
--   scope_unsupported_country     106 companies 3.02%    11 companies 0.37%
--   scope_industry_other          346 companies 9.85%    216 companies 7.31%
--   free_tier_row_cap             784 of 830 scored      750 of 830 scored
--
-- The enrichment codes are quoted against "the 16 companies Clay reached",
-- a number no view produces. Clay was sent 50 and returned 13 enriched.
--
-- And one code is missing outright. Migration 007 introduced
-- clay_credits_exhausted, which v_funnel names twice: the 34 companies sent to
-- Clay that never came back, and the 5 dedupe survivors with no copy. It was
-- never added here, so the funnel again names a code the code list does not
-- have. That is the exact fault migration 006 existed to remove, reintroduced
-- three migrations later.
--
-- WHAT IT DOES
--
-- Adds clay_credits_exhausted and re-reads every rate from v_funnel. Nothing
-- is deleted. seq is renumbered so the four dedupe codes sit after the new
-- one, in the order the funnel reports them.
--
-- Every figure below was read from v_funnel on 2026-09-06 by running the
-- verification query at the foot of this file, not carried over from a design.
--
-- Revert: db/revert_009.sql restores the eleven rows exactly as migration 006
-- left them.

begin;

-- Reachable twice over: 34 of the 50 sent to Clay never came back, and 5 of
-- the 10 companies that survived the dedupe have no copy. Both are the same
-- condition, which is that the free tier's credits ran out mid-run.
insert into reason_codes (code, stage, exits_to_table, description, measured_rate, seq) values
 ('clay_credits_exhausted', 'enrich', null,
  'Sent to Clay but the free tier credits ran out before the row was finished. Some came back with nothing at all; others resolved a domain and an email but never got copy. A budget boundary, not a failed enrichment.',
  '34 of the 50 sent returned nothing, and 5 of the 10 dedupe survivors have no copy', 8)
on conflict (code) do update
   set stage = excluded.stage,
       exits_to_table = excluded.exits_to_table,
       description = excluded.description,
       measured_rate = excluded.measured_rate,
       seq = excluded.seq;

-- The four route-out rates, re-read as companies against the 2,953 ingested.
update reason_codes set measured_rate = '1,664 companies, 56.35% of ingested'
 where code = 'scope_pooled_investment_fund';
update reason_codes set measured_rate = '232 companies, 7.86% of ingested'
 where code = 'scope_non_us_incorporation';
update reason_codes set measured_rate = '11 companies, 0.37% of ingested'
 where code = 'scope_unsupported_country';
update reason_codes set measured_rate = '216 companies, 7.31% of ingested'
 where code = 'scope_industry_other';

-- 750 were never sent, and the 34 that were sent are now their own code above.
update reason_codes
   set description = 'Never sent to Clay: the row did not fit inside the 200-row free table. A budget boundary, not a failed enrichment.',
       measured_rate = '750 of the 830 scored, 25.40% of ingested'
 where code = 'free_tier_row_cap';

-- Quoted against what Clay was actually given.
update reason_codes set measured_rate = '0 of the 50 sent to Clay'
 where code = 'enrich_no_domain';
update reason_codes set measured_rate = '3 of the 50 sent to Clay'
 where code = 'enrich_no_work_email';

-- The three seeded dedupe codes each fired once against the 13 enriched.
update reason_codes
   set measured_rate = '1 of the 13 enriched, against a seeded customer. Never measured naturally at this volume',
       seq = 9
 where code = 'dupe_existing_customer';
update reason_codes
   set measured_rate = '1 of the 13 enriched, against a seeded inbound company. Never measured naturally at this volume',
       seq = 10
 where code = 'dupe_inbound';
update reason_codes
   set measured_rate = '30 of the 830 scored, across 4 signers',
       seq = 11
 where code = 'dupe_same_signer';
update reason_codes
   set measured_rate = '1 of the 13 enriched, against a seeded address. Never measured naturally at this volume',
       seq = 12
 where code = 'dupe_already_emailed';

commit;


-- Verification. Run all three and read them against the numbers above.
--
--   select code, seq, measured_rate from reason_codes order by seq;
--   -- expects 12 rows, seq 1 to 12 with no gaps
--
--   select distinct reason_code from v_funnel
--    where reason_code is not null
--      and reason_code not in (select code from reason_codes);
--   -- expects zero rows: no code the funnel names is missing here
--
--   select level, stage, reason_code, companies from v_funnel order by seq;
--   -- every figure quoted in this file appears in that output
