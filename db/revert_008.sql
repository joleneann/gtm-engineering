-- Revert 008: put v_funnel back to the migration 007 definition.
--
-- Apply through the Supabase SQL editor.
--
-- This REINTRODUCES the fault 008 fixed: the ingested row returns to the
-- 'all companies' level alongside the five rows that partition it, so that
-- level sums to 5906 rather than 2953. Only run this if 008 broke something
-- that mattered more.
--
-- No table, column or constraint is touched either way.

drop view if exists v_funnel;

create or replace view v_funnel with (security_invoker = on) as
with base as (
  -- Every company EDGAR gave us, from every filing row: primary issuers,
  -- co-issuers, and the prior filings pulled for the 12-month rollup.
  select distinct cik from filings_raw
),
placed as (
  select b.cik,
         case
           when s.cik is not null then 6
           when p.cik is not null then 5
           when u.cik is not null and u.jurisdiction_fail then 3
           when u.cik is not null then 4
           when f.cik is not null then 2
           else 99
         end as gate
    from base b
    left join (select distinct cik from outbound_companies_scored) s on s.cik = b.cik
    left join (select distinct cik from no_industry_companies)     p on p.cik = b.cik
    left join likely_unserviceable_companies                       u on u.cik = b.cik
    left join (select distinct cik from formd_funds)               f on f.cik = b.cik
),
n as (
  select (select count(*) from base)                                     as ingested,
         (select count(*) from outbound_companies_scored)                as scored,
         (select count(*) from outbound_companies_scored
           where sent_to_clay_at is not null)                            as sent,
         (select count(*) from outbound_companies_scored
           where enrichment_status = 'enriched')                         as enriched,
         (select count(*) from outbound_companies_scored
           where enrichment_status = 'enriched'
             and dedupe_status = 'unique')                               as survived_dedupe
),
stages as (
  -- LEVEL 1: every company, counted once, at the furthest gate it reached.
  select  1 as seq, 'all companies' as level, 'ingested' as stage,
          null::text as reason_code, (select ingested from n) as companies,
          (select ingested from n) as level_base
  union all
  select  2, 'all companies', 'routed_out', 'scope_pooled_investment_fund',
          count(*), (select ingested from n) from placed where gate = 2
  union all
  select  3, 'all companies', 'routed_out', 'scope_non_us_incorporation',
          count(*), (select ingested from n) from placed where gate = 3
  union all
  select  4, 'all companies', 'routed_out', 'scope_unsupported_country',
          count(*), (select ingested from n) from placed where gate = 4
  union all
  select  5, 'all companies', 'parked', 'scope_industry_other',
          count(*), (select ingested from n) from placed where gate = 5
  union all
  select  6, 'all companies', 'scored', null,
          count(*), (select ingested from n) from placed where gate = 6

  -- LEVEL 2: what happened to the scored. Adds to the scored count.
  union all
  select  7, 'of the scored', 'held_back', 'dupe_same_signer',
          count(*), (select scored from n)
    from  outbound_companies_scored
   where  dedupe_status = 'dupe_same_signer'
  union all
  select  8, 'of the scored', 'never_sent_to_clay', 'free_tier_row_cap',
          count(*), (select scored from n)
    from  outbound_companies_scored
   where  sent_to_clay_at is null
     and  dedupe_status <> 'dupe_same_signer'
  union all
  select  9, 'of the scored', 'sent_to_clay', null,
          count(*), (select scored from n)
    from  outbound_companies_scored
   where  sent_to_clay_at is not null

  -- LEVEL 3: what Clay returned. Adds to the sent count.
  union all
  select 10, 'of those sent to Clay', 'no_return', 'clay_credits_exhausted',
          count(*), (select sent from n)
    from  outbound_companies_scored
   where  sent_to_clay_at is not null
     and  returned_from_clay_at is null
  union all
  select 11, 'of those sent to Clay', 'enrich_failed', enrichment_status,
          count(*), (select sent from n)
    from  outbound_companies_scored
   where  sent_to_clay_at is not null
     and  enrichment_status in ('enrich_no_domain', 'enrich_no_work_email')
   group  by enrichment_status
  union all
  select 12, 'of those sent to Clay', 'enriched', null,
          count(*), (select sent from n)
    from  outbound_companies_scored
   where  sent_to_clay_at is not null
     and  enrichment_status = 'enriched'

  -- LEVEL 4: the dedupe. Adds to the enriched count.
  union all
  select 13, 'of the enriched', 'removed', dedupe_status,
          count(*), (select enriched from n)
    from  outbound_companies_scored
   where  enrichment_status = 'enriched'
     and  dedupe_status in ('dupe_existing_customer', 'dupe_inbound', 'dupe_already_emailed')
   group  by dedupe_status
  union all
  select 14, 'of the enriched', 'survived_dedupe', null,
          count(*), (select enriched from n)
    from  outbound_companies_scored
   where  enrichment_status = 'enriched'
     and  dedupe_status = 'unique'

  -- LEVEL 5: copy is what makes a row sendable. Adds to the survivor count.
  union all
  select 15, 'of those that survived dedupe', 'has_copy', null,
          count(*), (select survived_dedupe from n)
    from  outbound_companies_scored
   where  enrichment_status = 'enriched'
     and  dedupe_status = 'unique'
     and  copy_body is not null
  union all
  select 16, 'of those that survived dedupe', 'no_copy', 'clay_credits_exhausted',
          count(*), (select survived_dedupe from n)
    from  outbound_companies_scored
   where  enrichment_status = 'enriched'
     and  dedupe_status = 'unique'
     and  copy_body is null
)
select seq,
       level,
       stage,
       reason_code,
       companies,
       round(100.0 * companies / nullif(level_base, 0), 2) as pct_of_level,
       round(100.0 * companies / nullif((select ingested from n), 0), 2) as pct_of_ingested
  from stages
 where companies > 0
 order by seq, reason_code;


comment on view v_funnel is
'Companies, never filings, counted once each at the furthest gate they reached. '
'Rows within one level add to that level base exactly; levels never add across. '
'Rebuilt 2026-09-04: see db/migration_007_funnel_companies.sql for what was wrong.';
