-- Migration 007: rebuild v_funnel so it counts one thing, and so its rows can
-- be added up.
--
-- Apply through the Supabase SQL editor. Views only: no table, column or
-- constraint is touched.
--
-- WHAT WAS WRONG
--
-- 1. Mixed units under one column called `companies`. `ingested` (3,512),
--    `scope_pooled_investment_fund` (1,996) and `scope_industry_other` (346)
--    counted FILINGS. The two servicability rows counted COMPANIES, and
--    everything from `scored` down counted companies. Four of the six rows in
--    the top block were filings.
--
-- 2. The two servicability rows overlapped. 232 fail on incorporation and 106
--    on address, but only 243 distinct companies are in that table: 95 fail on
--    both and were counted twice.
--
-- 3. Because of 1 and 2, the top block added to 3,510 against an ingested
--    3,512. Two errors nearly cancelling is not a reconciliation.
--
-- 4. `never_sent_to_clay = 784` was false for 34 of those rows. They went to
--    Clay and came back with nothing. The view could not tell the difference
--    because sent_to_clay_at was null on all 830 rows; scripts/14 fills it.
--
-- 5. Rows 7 to 12 were a breakdown of row 6, not further subtractions from it,
--    and nothing in the output said so. Anyone reading it top to bottom as a
--    funnel got a number that did not reconcile, correctly concluded it was
--    broken, and had no way to see which half was at fault.
--
-- WHAT IT DOES NOW
--
-- Companies throughout, because the question this build asks is how many
-- businesses could be emailed, and one company files more than one Form D.
-- Databricks filed two on a single day.
--
-- A company that appears at two gates is counted at the FURTHEST one it
-- reached. Three companies have one filing routed out as a fund and another
-- filing that scored, and two are parked on one filing and scored on another.
-- If any filing survived, the company survived, so it is counted as scored and
-- nowhere else. First-gate-wins would have hidden five companies that are
-- genuinely contactable.
--
-- Every row carries the population it is a share of, in `level`. Rows inside
-- one level add to that level's base exactly, and levels never add across.
--
-- Revert: db/revert_007.sql restores the migration 003 version.

-- NOTE: the view is DROPPED first, not replaced. `create or replace view`
-- cannot add, rename or reorder a column, and this version adds `level` and
-- `pct_of_level`; Postgres answers 42P16, "cannot change name of view column".
-- Nothing depends on v_funnel, so the drop takes nothing with it.

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


-- Verification. Every level must reconcile against its own base.
--
--   select level, sum(companies) from v_funnel group by level;
--
--   all companies                  -> 2953  (= select count(distinct cik) from filings_raw)
--   of the scored                  ->  830
--   of those sent to Clay          ->   50
--   of the enriched                ->   13
--   of those that survived dedupe  ->   10
--
-- Run scripts/14_backfill_sent_to_clay.py FIRST. Without sent_to_clay_at the
-- sent level is empty and 'of the scored' reports every row as never sent.
