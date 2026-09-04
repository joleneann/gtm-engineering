-- Migration 003: rewrite v_funnel, add v_outreach.
--
-- Applied through the Supabase SQL editor, never by a script.
--
-- Why: v_funnel lost 814 of the 830 scored companies and overstated its last
-- stage. It counted the unenriched as not_selected / enrich_no_domain /
-- enrich_no_work_email, and no script ever writes not_selected, so the 814
-- rows still sitting at 'pending' matched no line at all. It also called 10
-- rows dispatchable from enrichment and dedupe alone, when 5 of those had a
-- verified address and no copy and could never be sent to.
--
-- Diff: v_funnel replaced. Stages 7, 8 and 12 are new (held_back,
-- never_sent_to_clay, has_copy), the removed stage now includes
-- dupe_already_emailed, and every row carries pct_of_ingested. v_outreach is
-- new. No table, column or constraint is touched. Views only.
--
-- Revert:
--   drop view if exists v_outreach;
--   then restore the previous v_funnel from git history:
--   git show 2ce1378:db/schema.sql

-- Where every company went, ingest to an email that could actually be sent.
--
-- Corrected 2026-09-04. The previous version lost 814 of 830 scored companies
-- and overstated the last stage. It counted the unenriched as
-- not_selected / enrich_no_domain / enrich_no_work_email, and no script ever
-- writes not_selected: 780 companies were never sent to Clay because only 50
-- fit the free tier, and 34 were sent but Clay ran out of credits first. All
-- 814 are still 'pending' and matched no line, so they were counted nowhere.
-- It also called 10 rows dispatchable on enrichment and dedupe alone, when 5 of
-- them had a verified address and no copy, so nothing could be sent to them.
--
-- Two stages are named for what actually happened rather than for a status:
-- never_sent_to_clay is a budget boundary, not a resolution failure, and
-- has_copy is the only count from which an email can leave.
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


-- Every stage a company reaches once it is in the CRM.
--
-- Grouped this way because it is what makes the compliance rule readable in
-- SQL rather than asserted in prose: real companies sit at 'enriched' with
-- sent = 0, and every row with sent > 0 is a test row. A real company appearing
-- with sent > 0 would be the failure, and here it would be one line.
create or replace view v_outreach with (security_invoker = on) as
select  crm_stage,
        count(*)                                       as deals,
        count(*) filter (where is_test_row)            as test_rows,
        count(*) filter (where not is_test_row)        as real_companies,
        count(*) filter (where sent_at is not null)    as sent,
        count(*) filter (where replied_at is not null) as replied
  from  outbound_companies_scored
 where  pipedrive_deal_id is not null
 group  by crm_stage
 order  by crm_stage;


-- least() clamps a perfect 10.00 into the top bucket rather than letting
-- width_bucket push it to the out-of-range 11th.
create or replace view v_score_distribution with (security_invoker = on) as
select  least(width_bucket(score, 0, 10, 10), 10) as bucket,
        concat((least(width_bucket(score, 0, 10, 10), 10) - 1)::text, ' to ',
                least(width_bucket(score, 0, 10, 10), 10)::text) as score_range,
        count(*)             as companies,
        round(min(score), 2) as min_score,
        round(max(score), 2) as max_score
  from  outbound_companies_scored
 where  score is not null
 group  by 1
 order  by 1;
