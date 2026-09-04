-- Revert 003: drop v_outreach, restore v_funnel as it stood before migration 003.
--
-- This restores a view that loses 814 of 830 scored companies and reports 10
-- dispatchable when only 5 have copy. It exists so the change is reversible,
-- not because the old view was right.

drop view if exists v_outreach;

-- Where every company went, ingest to dispatchable. The Clay and dedupe
-- stages read 0 until enrichment runs and fill in on their own afterwards.
create or replace view v_funnel as
select  1 as seq, 'ingested'      as stage, null::text as reason_code,
        count(*) as companies
  from  filings_raw where is_primary_issuer
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
select  6, 'scored', null, count(*)
  from  outbound_companies_scored
union all
select  7, 'not_enriched', enrichment_status, count(*)
  from  outbound_companies_scored
 where  enrichment_status in ('not_selected', 'enrich_no_domain', 'enrich_no_work_email')
 group  by enrichment_status
union all
select  8, 'enriched', null, count(*)
  from  outbound_companies_scored where enrichment_status = 'enriched'
union all
select  9, 'removed', dedupe_status, count(*)
  from  outbound_companies_scored
 where  dedupe_status in ('dupe_existing_customer', 'dupe_inbound')
 group  by dedupe_status
union all
select 10, 'dispatchable', null, count(*)
  from  outbound_companies_scored
 where  enrichment_status = 'enriched' and dedupe_status = 'unique';
