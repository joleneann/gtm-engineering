-- Seed: serviceable_countries
-- Mercury's twelve serviceable countries, in EDGAR's own two-character codes.
--
-- WHERE THE CODE NAMES ARE LOGGED: table `edgar_codes`, seeded by
-- db/migration_002_edgar_codes.sql from the capture at
--   docs/sources/edgar_state_country_codes_2026-09-02.txt
-- Join to it to read a code as a place name:
--   select s.edgar_code, e.label, s.country_name
--     from serviceable_countries s join edgar_codes e on e.code = s.edgar_code;
--
-- The US is deliberately absent: a US address carries a state code and passes
-- the gate via us_jurisdictions. Canada is one country across twelve province
-- and federal codes, so the gate must match any of them.

insert into serviceable_countries (edgar_code, country_name) values
 ('X0','United Kingdom'),
 ('A0','Canada'),
 ('A1','Canada'),
 ('A2','Canada'),
 ('A3','Canada'),
 ('A4','Canada'),
 ('A5','Canada'),
 ('A6','Canada'),
 ('A7','Canada'),
 ('A8','Canada'),
 ('A9','Canada'),
 ('B0','Canada'),
 ('Z4','Canada'),
 ('K7','India'),
 ('U0','Singapore'),
 ('L3','Israel'),
 ('P7','Netherlands'),
 ('U3','Spain'),
 ('2M','Germany'),
 ('G7','Denmark'),
 ('C3','Australia'),
 ('O5','Mexico')
on conflict (edgar_code) do update set country_name = excluded.country_name;

update serviceable_countries
   set source_url = 'https://www.sec.gov/submit-filings/filer-support-resources/edgar-state-country-codes', captured_on = '2026-09-02';
