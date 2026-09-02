-- migration 005: one person, one email.
--
-- Apply in the Supabase SQL editor. Revert: db/revert_005.sql
--
-- PART A was already applied on 2026-09-02, straight from the proposal. It is
-- repeated here because this file, not a chat message, is the record of what
-- the database was asked to do. Every statement is idempotent, so re-running
-- the whole file is safe and changes nothing.
--
-- PART B was NOT in that proposal and still needs running: the two reason
-- codes. The dedupe_status constraint already accepts the values, so without
-- Part B a row could be marked with a code the registry does not contain,
-- which is exactly the runtime-minted code the contract forbids.
--
-- WHY
-- One human signs Form D for many companies. Measured across the 830 scored:
-- Rezwan Manji signs for 19, Alfonso Cahero 7, Christopher Kane 4, Tadd Miller
-- 4. Those 34 companies name 7 distinct humans between them, and Cahero's
-- seven name the same two people every time. Emailing per company means 60
-- emails to 7 people.
--
-- Corroborated independently by mill_list: of Manji's 19 companies, 16 had
-- already lost their address for being shared by more than three companies.
-- All 7 of Cahero's had. All 4 of Kane's had.
--
-- THRESHOLD: more than three companies. Two and three are allowed through
-- deliberately (30 signers, 70 companies, up to 40 extra emails), because the
-- contacted_emails check downstream catches them precisely once an address
-- exists, and it catches them on better evidence than a name.
--
-- DIFF: 2 tables added, 2 columns added, 1 check constraint widened, 2 reason
-- codes seeded. No table is dropped, no column is removed, no row is deleted.

begin;

-- ---------------------------------------------------------------- PART A
-- Applied 2026-09-02. Idempotent, so running it again is a no-op.

create table if not exists signer_list (
    normalised_signer   text     primary key,
    raw_examples        text[],
    company_count       integer  not null,
    company_ciks        bigint[],
    first_seen          date,
    last_seen           date,
    updated_at          timestamptz not null default now()
);

create table if not exists contacted_emails (
    email_normalised    text     primary key,
    cik                 bigint,
    company_name        text,
    first_contacted_at  timestamptz not null default now(),
    last_contacted_at   timestamptz not null default now(),
    times_contacted     integer  not null default 1,
    source              text     not null default 'outbound',
    is_demo_seed        boolean  not null default false
);

alter table outbound_companies_scored
    add column if not exists collapsed_into_cik bigint,
    add column if not exists also_signed_for    text[];

alter table outbound_companies_scored drop constraint if exists scored_dedupe_status_chk;
alter table outbound_companies_scored add constraint scored_dedupe_status_chk
    check (dedupe_status in ('pending', 'unique', 'dupe_existing_customer',
                             'dupe_inbound', 'dupe_same_signer', 'dupe_already_emailed'));

-- ---------------------------------------------------------------- PART B
-- Still to apply. The registry is closed: no script mints a code at runtime,
-- so a code must exist here before any row can carry it.

insert into reason_codes (code, stage, exits_to_table, description, measured_rate, seq) values
 ('dupe_same_signer',     'dedupe', null,
  'One human signs Form D for more than three companies. The highest scoring is contacted, the rest are kept and point at it.',
  '30 of 830 companies, across 4 signers', 10),
 ('dupe_already_emailed', 'dedupe', null,
  'The resolved work email is already in contacted_emails, so this person has been written to before.',
  'unmeasured until Clay returns addresses and the demo seed is added', 11)
on conflict (code) do update
   set stage = excluded.stage,
       exits_to_table = excluded.exits_to_table,
       description = excluded.description,
       measured_rate = excluded.measured_rate,
       seq = excluded.seq;

commit;

-- verification: expect 11 reason codes, both new ones present, the two tables
-- empty until 05_collapse_signers.py runs, and the two new columns on the
-- scored table.
select (select count(*) from reason_codes)                                as reason_codes,
       (select count(*) from reason_codes
         where code in ('dupe_same_signer','dupe_already_emailed'))       as new_codes,
       (select count(*) from signer_list)                                 as signer_rows,
       (select count(*) from contacted_emails)                            as contacted_rows,
       (select count(*) from information_schema.columns
         where table_name = 'outbound_companies_scored'
           and column_name in ('collapsed_into_cik','also_signed_for'))   as new_columns;
