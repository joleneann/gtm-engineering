-- =====================================================================
-- Revert of db/schema.sql version 001
--
-- Drops everything 001 created, children before parents. Destroys all data
-- in these tables. Applied by hand in the Supabase SQL editor.
-- =====================================================================

drop view if exists v_score_distribution;
drop view if exists v_funnel;

drop table if exists mercury_inbound;
drop table if exists existing_mercury_customers;
drop table if exists mill_list;
drop table if exists outbound_companies_scored;
drop table if exists outbound_companies_unscored;
drop table if exists likely_unserviceable_companies;
drop table if exists no_industry_companies;
drop table if exists formd_funds;

drop table if exists industry_scores;
drop table if exists industry_clusters;
drop table if exists us_jurisdictions;
drop table if exists serviceable_countries;
drop table if exists reason_codes;

drop table if exists entities_raw;
drop table if exists filing_former_names;
drop table if exists filing_related_persons;
drop table if exists filings_raw;
