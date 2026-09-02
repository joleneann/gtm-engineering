-- Revert of migration 002
alter table serviceable_countries drop constraint if exists serviceable_countries_code_fk;
drop table if exists edgar_codes;
