-- Revert of db/migration_009_reason_codes_from_funnel.sql.
--
-- Restores the eleven rows exactly as migration 006 left them, and drops
-- clay_credits_exhausted.
--
-- Reinstates the fault: v_funnel names clay_credits_exhausted twice, so after
-- this runs the funnel again reports a code the code list does not have, and
-- five measured rates again contradict the view they were read from.

begin;

delete from reason_codes where code = 'clay_credits_exhausted';

update reason_codes set measured_rate = '1,996 filings, 56.83% of ingested'
 where code = 'scope_pooled_investment_fund';
update reason_codes set measured_rate = '232 companies, 6.61% of ingested'
 where code = 'scope_non_us_incorporation';
update reason_codes set measured_rate = '106 companies, 3.02% of ingested'
 where code = 'scope_unsupported_country';
update reason_codes set measured_rate = '346 companies, 9.85% of ingested'
 where code = 'scope_industry_other';

update reason_codes
   set description = 'Never sent to Clay. 780 did not fit the 200-row free table and 34 were sent but the credits ran out first. A budget boundary, not a failed enrichment.',
       measured_rate = '784 of 830 scored, 22.32% of ingested'
 where code = 'free_tier_row_cap';

update reason_codes set measured_rate = '0 of the 16 companies Clay reached'
 where code = 'enrich_no_domain';
update reason_codes set measured_rate = '3 of the 16 companies Clay reached'
 where code = 'enrich_no_work_email';

update reason_codes
   set measured_rate = '1 row, against a seeded customer. Never measured naturally at this volume',
       seq = 8
 where code = 'dupe_existing_customer';
update reason_codes
   set measured_rate = '1 row, against a seeded inbound company. Never measured naturally at this volume',
       seq = 9
 where code = 'dupe_inbound';
update reason_codes
   set measured_rate = '30 of 830 companies, across 4 signers',
       seq = 10
 where code = 'dupe_same_signer';
update reason_codes
   set measured_rate = '1 row, against a seeded address. Never measured naturally at this volume',
       seq = 11
 where code = 'dupe_already_emailed';

commit;
