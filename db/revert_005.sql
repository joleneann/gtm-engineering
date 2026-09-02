-- revert 005: undo the signer collapse and the already-emailed check.
--
-- Reverting means one human can again receive one email per company he signs
-- for, which measured at 60 emails to 7 people. Only run this to undo a
-- mistaken apply.
--
-- Rows already marked dupe_same_signer are returned to 'pending' first,
-- because the constraint will not accept them once the value is removed.

begin;

update outbound_companies_scored
   set dedupe_status = 'pending',
       collapsed_into_cik = null
 where dedupe_status in ('dupe_same_signer', 'dupe_already_emailed');

alter table outbound_companies_scored drop constraint if exists scored_dedupe_status_chk;
alter table outbound_companies_scored add constraint scored_dedupe_status_chk
    check (dedupe_status in ('pending', 'unique',
                             'dupe_existing_customer', 'dupe_inbound'));

alter table outbound_companies_scored
    drop column if exists collapsed_into_cik,
    drop column if exists also_signed_for;

delete from reason_codes where code in ('dupe_same_signer', 'dupe_already_emailed');

drop table if exists signer_list;
drop table if exists contacted_emails;

commit;
