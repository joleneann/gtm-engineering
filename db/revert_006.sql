-- Revert 006: put reason_codes back exactly as db/schema.sql seeds it.
--
-- Restores `not_selected`, removes `free_tier_row_cap`, and returns every
-- measured_rate to its pre-migration wording.

begin;

insert into reason_codes (code, stage, exits_to_table, description, measured_rate, seq) values
 ('not_selected', 'enrich', null,
  'Scored but below the cutoff for a Clay enrichment slot.',
  '~900 scored against a 200-row Clay free tier', 5)
on conflict (code) do update
   set stage = excluded.stage,
       exits_to_table = excluded.exits_to_table,
       description = excluded.description,
       measured_rate = excluded.measured_rate,
       seq = excluded.seq;

delete from reason_codes where code = 'free_tier_row_cap';

update reason_codes set measured_rate = '62% of filings (120/193 and 103/165)'
 where code = 'scope_pooled_investment_fund';
update reason_codes set measured_rate = '10% of 40 companies sampled'
 where code = 'scope_non_us_incorporation';
update reason_codes set measured_rate = '5% of 40 companies sampled'
 where code = 'scope_unsupported_country';
update reason_codes set measured_rate = '18-24% of operating companies (13/73 and 15/62)'
 where code = 'scope_industry_other';
update reason_codes set measured_rate = 'unmeasured until Clay runs'
 where code = 'enrich_no_domain';
update reason_codes set measured_rate = 'unmeasured until Clay runs'
 where code = 'enrich_no_work_email';
update reason_codes
   set measured_rate = 'unmeasured until Clay returns addresses and the demo seed is added'
 where code = 'dupe_already_emailed';
update reason_codes set measured_rate = 'guaranteed by the 3 seeded customers'
 where code = 'dupe_existing_customer';
update reason_codes set measured_rate = 'guaranteed by the 2 seeded inbound rows'
 where code = 'dupe_inbound';

commit;
