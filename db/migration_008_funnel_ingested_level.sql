-- Migration 008: stop v_funnel's first level double counting.
--
-- Apply through the Supabase SQL editor. One view. No table, column or
-- constraint is touched.
--
-- WHAT IS WRONG
--
-- Migration 007 put six rows in the level called 'all companies':
--
--   ingested                                             2953
--   routed_out  scope_pooled_investment_fund             1664
--   routed_out  scope_non_us_incorporation                232
--   routed_out  scope_unsupported_country                  11
--   parked      scope_industry_other                      216
--   scored                                                830
--
-- The bottom five partition the top one: 1664 + 232 + 11 + 216 + 830 = 2953.
-- So the level sums to 5906, which is 2953 counted twice.
--
-- Every other level is correct, because no other level carries a base row:
-- 'of the scored' sums to 830, 'of those sent to Clay' to 50, 'of the
-- enriched' to 13, 'of those that survived dedupe' to 10.
--
-- Migration 007's own verification comment asserts that 'all companies' sums
-- to 2953. It does not, and never did. The comment was written from the design
-- rather than from a run, which is the exact failure that block exists to
-- catch. It is corrected in that file in the same commit as this one.
--
-- WHAT IT DOES
--
-- Moves the ingested row into a level of its own, named 'ingested'. Nothing
-- else changes: same rows, same counts, same order, same column list.
--
-- After this, every level sums to the population it describes, and 'ingested'
-- and 'all companies' both come to 2953 because the second is a partition of
-- the first.
--
-- Revert: db/revert_008.sql restores the migration 007 wording.

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
  -- LEVEL 0: the population everything below is a share of. Its own level,
  -- because the rows under 'all companies' add up to exactly this number and
  -- putting it beside them counts it twice.
  select  1 as seq, 'ingested' as level, 'ingested' as stage,
          null::text as reason_code, (select ingested from n) as companies,
          (select ingested from n) as level_base

  -- LEVEL 1: every company, counted once, at the furthest gate it reached.
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
'Every level sums to the population it describes; levels never add across. '
'Rebuilt 2026-09-04 (migration 007) and corrected 2026-09-05 (migration 008), '
'which moved the ingested row out of the level its own parts add up to.';


-- Verification. Run this and read it against the numbers below. Both were
-- produced by running it, not by reading the SQL.
--
--   select level, sum(companies) from v_funnel group by level;
--
--   ingested                       -> 2953  (= select count(distinct cik) from filings_raw)
--   all companies                  -> 2953
--   of the scored                  ->  830
--   of those sent to Clay          ->   50
--   of the enriched                ->   13
--   of those that survived dedupe  ->   10
--
-- 'ingested' and 'all companies' are equal on purpose: the second is a
-- partition of the first. Every other level is a partition of the row above it.
