-- Revert 007: restore the migration 003 v_funnel exactly.
--
-- This puts back the version that mixes filings and companies under one
-- `companies` column, double-counts the 95 companies failing both servicability
-- tests, and reports 34 companies that went to Clay as never sent. Reverting is
-- restoring those faults, and they are listed here so that is a decision rather
-- than a surprise.
--
-- sent_to_clay_at is left populated. The old view does not read it, and
-- emptying a column that records a real event to suit an older view would be
-- destroying data to make a report look consistent.

drop view if exists v_funnel;

create or replace view v_funnel with (security_invoker = on) as
with stages as (
  select  1 as seq, 'ingested' as stage, null::text as reason_code,
          (select count(*) from filings_raw where is_primary_issuer) as companies
  union all
  select  2, 'routed_out', reason_code, count(*)
    from  formd_funds group by reason_code
  union all
  select  3, 'routed_out', 'scope_non_us_incorporation', count(*)
    from  likely_unserviceable_companies where jurisdiction_fail
  union all
  select  4, 'routed_out', 'scope_unsupported_country', count(*)
    from  likely_unserviceable_companies where address_fail
  union all
  select  5, 'parked', reason_code, count(*)
    from  no_industry_companies group by reason_code
  union all
  select  6, 'scored', null, (select count(*) from outbound_companies_scored)
  union all
  select  7, 'held_back', 'dupe_same_signer', count(*)
    from  outbound_companies_scored where dedupe_status = 'dupe_same_signer'
  union all
  select  8, 'never_sent_to_clay', 'free_tier_row_cap', count(*)
    from  outbound_companies_scored
   where  enrichment_status = 'pending'
     and  dedupe_status <> 'dupe_same_signer'
  union all
  select  9, 'enrich_failed', enrichment_status, count(*)
    from  outbound_companies_scored
   where  enrichment_status in ('not_selected', 'enrich_no_domain', 'enrich_no_work_email')
   group  by enrichment_status
  union all
  select 10, 'enriched', null, count(*)
    from  outbound_companies_scored where enrichment_status = 'enriched'
  union all
  select 11, 'removed', dedupe_status, count(*)
    from  outbound_companies_scored
   where  dedupe_status in ('dupe_existing_customer', 'dupe_inbound', 'dupe_already_emailed')
   group  by dedupe_status
  union all
  select 12, 'has_copy', null, count(*)
    from  outbound_companies_scored
   where  enrichment_status = 'enriched'
     and  dedupe_status = 'unique'
     and  copy_body is not null
)
select  seq, stage, reason_code, companies,
        round(100.0 * companies
              / nullif(first_value(companies) over (order by seq), 0), 2) as pct_of_ingested
  from  stages
 order  by seq, reason_code;


comment on view v_funnel is null;
