-- Seed: serviceable_countries
-- Mercury's twelve serviceable countries, in EDGAR's own two-character codes.
--
-- WHERE THE CODE NAMES ARE LOGGED: table `edgar_codes`, seeded by
-- db/migration_002_edgar_codes.sql from the capture at
--   docs/sources/edgar_state_country_codes_2026-09-02.txt
-- Read a code as a place name by joining to it:
--   select s.edgar_code, e.label, s.country_name
--     from serviceable_countries s
--     join edgar_codes e on e.code = s.edgar_code
--    order by s.country_name;
--
-- The US is deliberately absent: a US address carries a state code and passes
-- the gate via us_jurisdictions. Canada is one country across twelve province
-- and federal codes, so the gate must match any of them.
--
-- 22 rows. Safe to re-run: every row is upserted on its primary key and there
-- is no unqualified UPDATE.

insert into serviceable_countries
    (edgar_code, country_name, source_url, captured_on) values
 ('X0','United Kingdom','https://www.sec.gov/submit-filings/filer-support-resources/edgar-state-country-codes','2026-09-02'),
 ('A0','Canada','https://www.sec.gov/submit-filings/filer-support-resources/edgar-state-country-codes','2026-09-02'),
 ('A1','Canada','https://www.sec.gov/submit-filings/filer-support-resources/edgar-state-country-codes','2026-09-02'),
 ('A2','Canada','https://www.sec.gov/submit-filings/filer-support-resources/edgar-state-country-codes','2026-09-02'),
 ('A3','Canada','https://www.sec.gov/submit-filings/filer-support-resources/edgar-state-country-codes','2026-09-02'),
 ('A4','Canada','https://www.sec.gov/submit-filings/filer-support-resources/edgar-state-country-codes','2026-09-02'),
 ('A5','Canada','https://www.sec.gov/submit-filings/filer-support-resources/edgar-state-country-codes','2026-09-02'),
 ('A6','Canada','https://www.sec.gov/submit-filings/filer-support-resources/edgar-state-country-codes','2026-09-02'),
 ('A7','Canada','https://www.sec.gov/submit-filings/filer-support-resources/edgar-state-country-codes','2026-09-02'),
 ('A8','Canada','https://www.sec.gov/submit-filings/filer-support-resources/edgar-state-country-codes','2026-09-02'),
 ('A9','Canada','https://www.sec.gov/submit-filings/filer-support-resources/edgar-state-country-codes','2026-09-02'),
 ('B0','Canada','https://www.sec.gov/submit-filings/filer-support-resources/edgar-state-country-codes','2026-09-02'),
 ('Z4','Canada','https://www.sec.gov/submit-filings/filer-support-resources/edgar-state-country-codes','2026-09-02'),
 ('K7','India','https://www.sec.gov/submit-filings/filer-support-resources/edgar-state-country-codes','2026-09-02'),
 ('U0','Singapore','https://www.sec.gov/submit-filings/filer-support-resources/edgar-state-country-codes','2026-09-02'),
 ('L3','Israel','https://www.sec.gov/submit-filings/filer-support-resources/edgar-state-country-codes','2026-09-02'),
 ('P7','Netherlands','https://www.sec.gov/submit-filings/filer-support-resources/edgar-state-country-codes','2026-09-02'),
 ('U3','Spain','https://www.sec.gov/submit-filings/filer-support-resources/edgar-state-country-codes','2026-09-02'),
 ('2M','Germany','https://www.sec.gov/submit-filings/filer-support-resources/edgar-state-country-codes','2026-09-02'),
 ('G7','Denmark','https://www.sec.gov/submit-filings/filer-support-resources/edgar-state-country-codes','2026-09-02'),
 ('C3','Australia','https://www.sec.gov/submit-filings/filer-support-resources/edgar-state-country-codes','2026-09-02'),
 ('O5','Mexico','https://www.sec.gov/submit-filings/filer-support-resources/edgar-state-country-codes','2026-09-02')
on conflict (edgar_code) do update
   set country_name = excluded.country_name,
       source_url   = excluded.source_url,
       captured_on  = excluded.captured_on;
