-- fix 004: four industry_scores codes carried the PDF's ampersands and could
-- never match a filing.
--
-- Apply in the Supabase SQL editor. Revert: db/revert_004.sql
--
-- WHY
-- The Form D PDF prints these groups with "&". The XML enum does not use it.
-- Measured two ways, both in docs/sources/edgar_industry_enum_spelling_2026-09-02.md:
--   EDGAR full-text search over form D returns 0 documents for every ampersand
--   spelling, against 153 / 819 / 365 / 1,232 for the "and" spelling; and no
--   ampersand appears in any of the 3,571 rows in filings_raw.
--
-- CONSEQUENCE BEFORE THE FIX
-- Four of the 33 scorable codes were dead. Two of them are present in the
-- current pull, so 4 companies could not be scored at all and 04_score.py
-- halted on them rather than scoring them zero, which is the guard working.
--
-- DIFF: 4 rows updated, no rows added or deleted, no DDL.
--   'Hospitals & Physicians'     -> 'Hospitals and Physicians'
--   'Airlines & Airports'        -> 'Airlines and Airports'
--   'Lodging & Conventions'      -> 'Lodging and Conventions'
--   'Tourism & Travel Services'  -> 'Tourism and Travel Services'
--
-- Safe to re-run: each statement matches on the old spelling, so a second run
-- updates nothing. industry_group_type is the primary key and nothing
-- references it by foreign key, so renaming the value is not a cascade.

begin;

update industry_scores set industry_group_type = 'Hospitals and Physicians'
 where industry_group_type = 'Hospitals & Physicians';

update industry_scores set industry_group_type = 'Airlines and Airports'
 where industry_group_type = 'Airlines & Airports';

update industry_scores set industry_group_type = 'Lodging and Conventions'
 where industry_group_type = 'Lodging & Conventions';

update industry_scores set industry_group_type = 'Tourism and Travel Services'
 where industry_group_type = 'Tourism & Travel Services';

commit;

-- verification: expect 33 rows, 0 of them containing an ampersand, and the
-- four corrected codes present.
select count(*)                                              as total_codes,
       count(*) filter (where industry_group_type like '%&%') as with_ampersand,
       count(*) filter (where industry_group_type in (
           'Hospitals and Physicians', 'Airlines and Airports',
           'Lodging and Conventions',  'Tourism and Travel Services'))
                                                              as corrected_present
  from industry_scores;
