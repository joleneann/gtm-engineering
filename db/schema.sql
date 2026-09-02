-- =====================================================================
-- GTM Engineering build: schema
-- Source of truth: docs/source_of_truth.md
--
-- Applied by hand in the Supabase SQL editor. Never by a script, never
-- through MCP. 17 tables, 2 views.
--
-- Version: 001
-- Date:    2026-09-02
-- Revert:  db/revert_001.sql
-- =====================================================================


-- ---------------------------------------------------------------------
-- 1. RAW: the documents, parsed into their constituent fields
-- ---------------------------------------------------------------------

-- One row per (filing, issuer). A co-issuer gets its own row under the
-- same accession with is_primary_issuer = false: several companies can be
-- listed in one filing when they sell in the same transaction, which is
-- why the key is compound.
create table if not exists filings_raw (
    accession_number                text        not null,
    cik                             bigint      not null,
    is_primary_issuer               boolean     not null default true,

    -- from the daily index
    form_type                       text        not null,
    filing_date                     date        not null,
    company_name_index              text,
    archive_path                    text,

    -- document envelope
    schema_version                  text,
    submission_type                 text,
    test_or_live                    text,
    is_amendment                    boolean,

    -- issuer
    entity_name                     text,
    entity_type                     text,
    entity_type_other_desc          text,
    jurisdiction_of_inc             text,
    issuer_phone                    text,
    year_of_inc_value               text,
    year_of_inc_within_five_years   boolean,
    year_of_inc_over_five_years     boolean,
    year_of_inc_yet_to_be_formed    boolean,
    issuer_street1                  text,
    issuer_street2                  text,
    issuer_city                     text,
    issuer_state_or_country         text,
    issuer_state_or_country_desc    text,
    issuer_zip                      text,

    -- offering
    industry_group_type             text,
    investment_fund_type            text,
    is_40_act                       boolean,
    revenue_range                   text,
    aggregate_net_asset_value_range text,
    date_of_first_sale              date,
    first_sale_yet_to_occur         boolean,
    duration_more_than_one_year     boolean,
    minimum_investment_accepted     numeric(20,2),
    total_offering_amount           numeric(20,2),
    total_amount_sold               numeric(20,2),
    total_remaining                 numeric(20,2),
    offering_amounts_clarification  text,
    has_non_accredited_investors    boolean,
    number_non_accredited_investors integer,
    total_number_already_invested   integer,

    -- securities offered
    is_equity_type                  boolean,
    is_debt_type                    boolean,
    is_option_to_acquire_type       boolean,
    is_security_to_be_acquired_type boolean,
    is_pooled_investment_fund_type  boolean,
    is_tenant_in_common_type        boolean,
    is_mineral_property_type        boolean,
    is_other_type                   boolean,
    description_of_other_type       text,

    -- exemptions claimed: bare repeating codes, e.g. 06b, 06c, 3C.7
    federal_exemptions              text[],

    -- business combination
    is_business_combination_transaction boolean,
    business_combination_clarification  text,

    -- commissions and proceeds
    sales_commissions_amount        numeric(20,2),
    sales_commissions_is_estimate   boolean,
    finders_fees_amount             numeric(20,2),
    finders_fees_is_estimate        boolean,
    commissions_clarification       text,
    gross_proceeds_used_amount      numeric(20,2),
    gross_proceeds_used_is_estimate boolean,
    use_of_proceeds_clarification   text,

    -- signature
    signature_issuer_name           text,
    name_of_signer                  text,
    signature_name                  text,
    signature_title                 text,
    signature_date                  date,
    authorized_representative       boolean,

    -- broker-dealer recipients: repeating, and nothing downstream reads it
    sales_compensation              jsonb,

    -- provenance
    pulled_reason                   text        not null default 'daily_index',
    fetched_at                      timestamptz not null default now(),

    constraint filings_raw_pk primary key (accession_number, cik),
    constraint filings_raw_pulled_reason_chk
        check (pulled_reason in ('daily_index', 'rollup_prior'))
);

create index if not exists filings_raw_cik_idx          on filings_raw (cik);
create index if not exists filings_raw_filing_date_idx  on filings_raw (filing_date);
create index if not exists filings_raw_industry_idx     on filings_raw (industry_group_type);


-- Related persons repeat inside a filing: median 2, max 15. 100% of
-- filings name at least one. This is what fills `people` for Clay.
create table if not exists filing_related_persons (
    accession_number        text        not null,
    cik                     bigint      not null,
    seq                     smallint    not null,
    first_name              text,
    middle_name             text,
    last_name               text,
    street1                 text,
    street2                 text,
    city                    text,
    state_or_country        text,
    state_or_country_desc   text,
    zip                     text,
    relationships           text[],
    relationship_clarification text,

    constraint filing_related_persons_pk primary key (accession_number, cik, seq),
    constraint filing_related_persons_fk foreign key (accession_number, cik)
        references filings_raw (accession_number, cik) on delete cascade
);

create index if not exists filing_related_persons_cik_idx on filing_related_persons (cik);


-- Former names repeat, and come from two places in the XML.
create table if not exists filing_former_names (
    accession_number    text        not null,
    cik                 bigint      not null,
    seq                 smallint    not null,
    previous_name       text        not null,
    source              text        not null,

    constraint filing_former_names_pk primary key (accession_number, cik, seq),
    constraint filing_former_names_fk foreign key (accession_number, cik)
        references filings_raw (accession_number, cik) on delete cascade,
    constraint filing_former_names_source_chk
        check (source in ('issuer_previous_name', 'edgar_previous_name'))
);


-- The company's submissions JSON, parsed into columns. One row per CIK.
-- state_of_incorporation is the jurisdiction gate; business_state_or_country
-- is the address gate. Both read from here, never from the filing, because a
-- filing address is often the filing agent's.
create table if not exists entities_raw (
    cik                             bigint      primary key,
    entity_name                     text,
    entity_type                     text,
    ein                             text,
    lei                             text,
    sic                             text,
    sic_description                 text,
    category                        text,
    description                     text,
    fiscal_year_end                 text,
    owner_org                       text,
    phone                           text,

    -- website is the only URL that reaches Clay. investor_website is parsed
    -- because the document is parsed whole, but it never leaves this table:
    -- it is an investor-relations page, not the company's domain.
    website                         text,
    investor_website                text,

    state_of_incorporation          text,
    state_of_incorporation_desc     text,

    business_street1                text,
    business_street2                text,
    business_city                   text,
    business_state_or_country       text,
    business_zip                    text,
    business_is_foreign             boolean,
    business_country                text,
    business_country_code           text,

    mailing_street1                 text,
    mailing_street2                 text,
    mailing_city                    text,
    mailing_state_or_country        text,
    mailing_zip                     text,
    mailing_is_foreign              boolean,
    mailing_country                 text,
    mailing_country_code            text,

    tickers                         text[],
    exchanges                       text[],
    former_names                    jsonb,

    -- [{accession, filing_date, form}] for form D and D/A only. Drives both
    -- the prior-filings score and the rollup's prior-filing fetch.
    form_d_history                  jsonb,
    total_form_d_count              integer,
    form_da_count                   integer,
    all_form_types                  text[],

    fetched_at                      timestamptz not null default now()
);


-- ---------------------------------------------------------------------
-- 2. REFERENCE: every rule that removes a company is data, not a constant
-- ---------------------------------------------------------------------

-- A reason code must be reachable at real volume, so each carries the rate
-- actually measured. A code for a condition that cannot occur is padding.
create table if not exists reason_codes (
    code            text    primary key,
    stage           text    not null,
    exits_to_table  text,
    description     text    not null,
    measured_rate   text    not null,
    seq             smallint not null
);

-- Mercury's twelve serviceable countries, in EDGAR's own two-character
-- codes. SEEDED IN STEP 3, not here: EDGAR encodes foreign locations with
-- its own code list, so 02_route.py first prints the distinct non-US values
-- actually present in the pull and they are mapped by hand before seeding.
-- 02_route.py fails loudly if this table is empty.
create table if not exists serviceable_countries (
    edgar_code      text    primary key,
    country_name    text    not null,
    source_url      text,
    captured_on     date
);

-- The US state and territory codes EDGAR uses in stateOfIncorporation.
-- A company fails scope_non_us_incorporation when its code is absent here.
create table if not exists us_jurisdictions (
    code            text    primary key,
    name            text    not null
);

-- The 8 clusters and the Mercury customers named publicly in each, so copy
-- can cite a real customer in the prospect's own segment.
create table if not exists industry_clusters (
    cluster_id      smallint primary key,
    cluster_name    text    not null unique,
    named_customers text[]  not null
);

-- The 33 scorable Form D industry codes. The 34th code on the form,
-- 'Other', is deliberately absent: those companies are parked, not scored.
-- 'Pooled Investment Fund' is routed out before scoring.
create table if not exists industry_scores (
    industry_group_type text        primary key,
    sec_group           text        not null,
    points              numeric(3,2) not null,
    cluster_id          smallint    references industry_clusters (cluster_id),
    rank                smallint    not null,
    constraint industry_scores_points_chk check (points >= 0 and points <= 3.00)
);


-- ---------------------------------------------------------------------
-- 3. ROUTED OUT: nothing is deleted, everything carries a reason
-- ---------------------------------------------------------------------

create table if not exists formd_funds (
    accession_number    text    not null,
    cik                 bigint  not null,
    company_name        text,
    filing_date         date,
    industry_group_type text,
    investment_fund_type text,
    is_40_act           boolean,
    is_pooled_tick      boolean,
    -- which of the two intent fields fired. The securities_tick-only rows are
    -- the funds the industry group alone would have missed.
    detected_by         text    not null,
    total_amount_sold   numeric(20,2),
    reason_code         text    not null references reason_codes (code),
    routed_at           timestamptz not null default now(),

    constraint formd_funds_pk primary key (accession_number, cik),
    constraint formd_funds_detected_by_chk
        check (detected_by in ('industry_group', 'securities_tick', 'both'))
);


-- industryGroupType = 'Other'. Parked, not discarded. Carries the full
-- candidate set so a later Clay industry-enrichment path can pick it up and
-- return it for scoring with no refetch.
create table if not exists no_industry_companies (
    accession_number        text    not null,
    cik                     bigint  not null,
    company_name            text,
    filing_date             date,
    industry_group_type     text,
    total_amount_sold       numeric(20,2),
    total_remaining         numeric(20,2),
    date_of_first_sale      date,
    first_sale_yet_to_occur boolean,
    prior_formd_count       integer,
    issuer_phone            text,
    issuer_street1          text,
    issuer_city             text,
    issuer_state_or_country text,
    issuer_zip              text,
    website_from_edgar      text,
    reason_code             text    not null references reason_codes (code),
    parked_at               timestamptz not null default now(),

    constraint no_industry_companies_pk primary key (accession_number, cik)
);


create table if not exists likely_unserviceable_companies (
    cik                         bigint  primary key,
    company_name                text,
    jurisdiction_of_inc         text,
    business_state_or_country   text,
    business_country_code       text,
    jurisdiction_fail           boolean not null default false,
    address_fail                boolean not null default false,
    -- comma-joined when both fired
    reason_code                 text    not null,
    routed_at                   timestamptz not null default now(),

    constraint likely_unserviceable_at_least_one_fail
        check (jurisdiction_fail or address_fail)
);


-- ---------------------------------------------------------------------
-- 4. THE PIPELINE
-- ---------------------------------------------------------------------

-- One row per filing. This is what the 12-month rollup groups over.
create table if not exists outbound_companies_unscored (
    accession_number            text    not null,
    cik                         bigint  not null,
    company_name                text,
    filing_date                 date    not null,
    date_of_first_sale          date,
    first_sale_yet_to_occur     boolean,
    total_offering_amount       numeric(20,2),
    total_amount_sold           numeric(20,2),
    total_remaining             numeric(20,2),
    total_number_already_invested integer,
    -- sha256 of (total_offering_amount, total_amount_sold, date_of_first_sale,
    -- total_number_already_invested): identifies the same offering refiled
    offering_fingerprint        text    not null,
    industry_group_type         text,
    entity_type                 text,
    issuer_street1              text,
    issuer_street2              text,
    issuer_city                 text,
    issuer_state_or_country     text,
    issuer_zip                  text,
    issuer_phone                text,
    name_of_signer              text,
    signature_title             text,
    authorized_representative   boolean,
    created_at                  timestamptz not null default now(),

    constraint outbound_companies_unscored_pk primary key (accession_number, cik)
);

create index if not exists outbound_unscored_cik_idx on outbound_companies_unscored (cik);
create index if not exists outbound_unscored_fp_idx  on outbound_companies_unscored (cik, offering_fingerprint);


-- One row per company. This is the Clay payload and the dispatch record.
create table if not exists outbound_companies_scored (
    cik                     bigint  primary key,

    -- Clay payload, names as specified in the source of truth
    current_name_candidates text[],
    former_name_candidates  text[],
    address_candidates      text[],
    phone_candidates        text[],
    website_from_edgar      text,
    contact_name            text,
    people                  jsonb,
    amount_sold             numeric(20,2),
    amount_remaining        numeric(20,2),
    industry                text,
    prior_formd_count       integer,
    filing_date             date,
    score                   numeric(4,2),

    -- the working
    score_amount            numeric(4,2),
    score_remaining         numeric(4,2),
    score_industry          numeric(4,2),
    score_prior             numeric(4,2),

    -- rollup provenance
    rolled_accessions       text[],
    rolled_filing_count     smallint,
    window_start            date,
    window_end              date,

    -- post-Clay
    domain                  text,
    work_email              text,
    copy_body               text,
    clay_row_id             text,
    sent_to_clay_at         timestamptz,
    returned_from_clay_at   timestamptz,

    enrichment_status       text    not null default 'pending',
    dedupe_status           text    not null default 'pending',
    dedupe_matched_on       text,
    dedupe_matched_id       bigint,

    is_test_row             boolean not null default false,
    scored_at               timestamptz not null default now(),

    constraint scored_score_range_chk
        check (score is null or (score >= 0 and score <= 10.00)),
    constraint scored_enrichment_status_chk
        check (enrichment_status in ('pending', 'not_selected', 'enriched',
                                     'enrich_no_domain', 'enrich_no_work_email')),
    constraint scored_dedupe_status_chk
        check (dedupe_status in ('pending', 'unique',
                                 'dupe_existing_customer', 'dupe_inbound')),
    constraint scored_dedupe_matched_on_chk
        check (dedupe_matched_on is null or dedupe_matched_on in ('domain', 'phone'))
);

create index if not exists scored_score_idx  on outbound_companies_scored (score desc);
create index if not exists scored_domain_idx on outbound_companies_scored (domain);


-- Addresses and phones belonging to filing agents and mills, not companies.
-- Threshold: more than three occurrences in the data.
create table if not exists mill_list (
    value_type          text    not null,
    normalised_value    text    not null,
    raw_examples        text[],
    occurrence_count    integer not null,
    distinct_cik_count  integer not null,
    first_seen          date,
    last_seen           date,
    updated_at          timestamptz not null default now(),

    constraint mill_list_pk primary key (value_type, normalised_value),
    constraint mill_list_value_type_chk check (value_type in ('address', 'phone'))
);


-- ---------------------------------------------------------------------
-- 5. DEDUPE TARGETS: seeded and already enriched for the demo
-- No cik column: the dedupe runs after Clay, on normalised apex domain.
-- ---------------------------------------------------------------------

create table if not exists existing_mercury_customers (
    id              bigserial primary key,
    company_name    text    not null,
    domain          text    not null,
    phone           text,
    contact_name    text,
    contact_email   text,
    industry        text,
    created_at      timestamptz not null default now()
);

create unique index if not exists existing_customers_domain_idx
    on existing_mercury_customers (lower(domain));


create table if not exists mercury_inbound (
    id                      bigserial primary key,
    company_name            text    not null,
    domain                  text    not null,
    phone                   text    not null,
    contact_name            text,
    contact_email           text,
    industry                text,
    expected_balance_band   text,
    source                  text,
    submitted_at            timestamptz,
    created_at              timestamptz not null default now()
);

create unique index if not exists mercury_inbound_domain_idx
    on mercury_inbound (lower(domain));


-- ---------------------------------------------------------------------
-- 6. VIEWS
-- ---------------------------------------------------------------------

-- Where every company went, ingest to dispatchable. The Clay and dedupe
-- stages read 0 until enrichment runs and fill in on their own afterwards.
create or replace view v_funnel as
select  1 as seq, 'ingested'      as stage, null::text as reason_code,
        count(*) as companies
  from  filings_raw where is_primary_issuer
union all
select  2, 'routed_out', reason_code, count(*)
  from  formd_funds group by reason_code
union all
select  3, 'routed_out', 'scope_non_us_incorporation', count(*)
  from  likely_unserviceable_companies where jurisdiction_fail
union all
select  4, 'routed_out', 'scope_unsupported_country', count(*)
  from  likely_unserviceable_companies where address_fail
union all
select  5, 'parked', reason_code, count(*)
  from  no_industry_companies group by reason_code
union all
select  6, 'scored', null, count(*)
  from  outbound_companies_scored
union all
select  7, 'not_enriched', enrichment_status, count(*)
  from  outbound_companies_scored
 where  enrichment_status in ('not_selected', 'enrich_no_domain', 'enrich_no_work_email')
 group  by enrichment_status
union all
select  8, 'enriched', null, count(*)
  from  outbound_companies_scored where enrichment_status = 'enriched'
union all
select  9, 'removed', dedupe_status, count(*)
  from  outbound_companies_scored
 where  dedupe_status in ('dupe_existing_customer', 'dupe_inbound')
 group  by dedupe_status
union all
select 10, 'dispatchable', null, count(*)
  from  outbound_companies_scored
 where  enrichment_status = 'enriched' and dedupe_status = 'unique';


-- least() clamps a perfect 10.00 into the top bucket rather than letting
-- width_bucket push it to the out-of-range 11th.
create or replace view v_score_distribution as
select  least(width_bucket(score, 0, 10, 10), 10) as bucket,
        concat((least(width_bucket(score, 0, 10, 10), 10) - 1)::text, ' to ',
                least(width_bucket(score, 0, 10, 10), 10)::text) as score_range,
        count(*)             as companies,
        round(min(score), 2) as min_score,
        round(max(score), 2) as max_score
  from  outbound_companies_scored
 where  score is not null
 group  by 1
 order  by 1;


-- =====================================================================
-- SEED: reference data
-- =====================================================================

insert into industry_clusters (cluster_id, cluster_name, named_customers) values
 (1, 'Technology',          array['Linear','Supabase','Sprig','Mona']),
 (2, 'Life Science',        array['Freedom Biosciences','TwoStep Therapeutics','Infinimmune']),
 (3, 'Healthcare Services', array['Assort Health','Mochi Health']),
 (4, 'Business Services',   array['Ways & Means','Acuity','IBEX Consulting']),
 (5, 'Ecommerce',           array['Manta Sleep','Minaal','Raide']),
 (6, 'Climate',             array['Patch','Zeno Power','Renuble']),
 (7, 'Real Estate',         array['KindDesigns','Blue Maple Rentals']),
 (8, 'Crypto / Fintech',    array['Phantom','CoinTracker','XMTP'])
on conflict (cluster_id) do update
   set cluster_name = excluded.cluster_name,
       named_customers = excluded.named_customers;


-- 33 codes. Values are the exact XML enum, verified against real filings,
-- which is why they read 'Oil and Gas' and 'REITS and Finance' and
-- 'Other Banking and Financial Services' rather than the PDF's ampersands.
insert into industry_scores (industry_group_type, sec_group, points, cluster_id, rank) values
 ('Other Technology',                     'Technology',                   3.00, 1,     1),
 ('Computers',                            'Technology',                   3.00, 1,     2),
 ('Biotechnology',                        'Health Care',                  2.70, 2,     3),
 ('Pharmaceuticals',                      'Health Care',                  2.70, 2,     4),
 ('Business Services',                    'Business Services',            2.55, 4,     5),
 ('Other Health Care',                    'Health Care',                  2.40, 3,     6),
 ('Health Insurance',                     'Health Care',                  2.40, 3,     7),
 ('Hospitals & Physicians',               'Health Care',                  2.40, 3,     8),
 ('Other Energy',                         'Energy',                       2.25, 6,     9),
 ('Energy Conservation',                  'Energy',                       2.25, 6,    10),
 ('Environmental Services',               'Energy',                       2.25, 6,    11),
 ('Electric Utilities',                   'Energy',                       2.25, 6,    12),
 ('Telecommunications',                   'Technology',                   2.10, 1,    13),
 ('Retailing',                            'Retailing',                    1.80, 5,    14),
 ('Other Banking and Financial Services', 'Banking & Financial Services', 1.50, 8,    15),
 ('Commercial',                           'Real Estate',                  1.20, 7,    16),
 ('Residential',                          'Real Estate',                  1.20, 7,    17),
 ('Construction',                         'Real Estate',                  1.20, 7,    18),
 ('REITS and Finance',                    'Real Estate',                  1.20, 7,    19),
 ('Other Real Estate',                    'Real Estate',                  1.20, 7,    20),
 ('Manufacturing',                        'Manufacturing',                0.90, null, 21),
 ('Agriculture',                          'Agriculture',                  0.90, null, 22),
 ('Restaurants',                          'Restaurants',                  0.90, null, 23),
 ('Airlines & Airports',                  'Travel',                       0.60, null, 24),
 ('Lodging & Conventions',                'Travel',                       0.60, null, 25),
 ('Tourism & Travel Services',            'Travel',                       0.60, null, 26),
 ('Other Travel',                         'Travel',                       0.60, null, 27),
 ('Oil and Gas',                          'Energy',                       0.30, null, 28),
 ('Coal Mining',                          'Energy',                       0.30, null, 29),
 ('Investing',                            'Banking & Financial Services', 0.30, null, 30),
 ('Commercial Banking',                   'Banking & Financial Services', 0.30, null, 31),
 ('Investment Banking',                   'Banking & Financial Services', 0.30, null, 32),
 ('Insurance',                            'Banking & Financial Services', 0.30, null, 33)
on conflict (industry_group_type) do update
   set sec_group = excluded.sec_group,
       points     = excluded.points,
       cluster_id = excluded.cluster_id,
       rank       = excluded.rank;


insert into reason_codes (code, stage, exits_to_table, description, measured_rate, seq) values
 ('scope_pooled_investment_fund', 'route',  'formd_funds',
  'Pooled investment fund by industry group or by the securities-offered tick. Out of scope for this build, not ineligible.',
  '62% of filings (120/193 and 103/165)', 1),
 ('scope_non_us_incorporation',   'route',  'likely_unserviceable_companies',
  'stateOfIncorporation is not a US state or territory code.',
  '10% of 40 companies sampled', 2),
 ('scope_unsupported_country',    'route',  'likely_unserviceable_companies',
  'Business address is outside Mercury''s twelve serviceable countries.',
  '5% of 40 companies sampled', 3),
 ('scope_industry_other',         'route',  'no_industry_companies',
  'industryGroupType = Other. Parked for a later Clay industry-enrichment path, not discarded.',
  '18-24% of operating companies (13/73 and 15/62)', 4),
 ('not_selected',                 'enrich', null,
  'Scored but below the cutoff for a Clay enrichment slot.',
  '~900 scored against a 200-row Clay free tier', 5),
 ('enrich_no_domain',             'enrich', null,
  'Clay could not resolve the company to a website.',
  'unmeasured until Clay runs', 6),
 ('enrich_no_work_email',         'enrich', null,
  'Domain resolved but no verified work email found.',
  'unmeasured until Clay runs', 7),
 ('dupe_existing_customer',       'dedupe', null,
  'Apex domain matches an existing Mercury customer.',
  'guaranteed by the 3 seeded customers', 8),
 ('dupe_inbound',                 'dedupe', null,
  'Apex domain matches a company that already came in through inbound.',
  'guaranteed by the 2 seeded inbound rows', 9)
on conflict (code) do update
   set stage = excluded.stage,
       exits_to_table = excluded.exits_to_table,
       description = excluded.description,
       measured_rate = excluded.measured_rate,
       seq = excluded.seq;


-- 50 states, DC, and the five inhabited territories. 02_route.py prints any
-- stateOfIncorporation value it sees that is absent from this table, so an
-- EDGAR code not anticipated here surfaces rather than silently failing a
-- company.
insert into us_jurisdictions (code, name) values
 ('AL','Alabama'),('AK','Alaska'),('AZ','Arizona'),('AR','Arkansas'),
 ('CA','California'),('CO','Colorado'),('CT','Connecticut'),('DE','Delaware'),
 ('DC','District of Columbia'),('FL','Florida'),('GA','Georgia'),('HI','Hawaii'),
 ('ID','Idaho'),('IL','Illinois'),('IN','Indiana'),('IA','Iowa'),
 ('KS','Kansas'),('KY','Kentucky'),('LA','Louisiana'),('ME','Maine'),
 ('MD','Maryland'),('MA','Massachusetts'),('MI','Michigan'),('MN','Minnesota'),
 ('MS','Mississippi'),('MO','Missouri'),('MT','Montana'),('NE','Nebraska'),
 ('NV','Nevada'),('NH','New Hampshire'),('NJ','New Jersey'),('NM','New Mexico'),
 ('NY','New York'),('NC','North Carolina'),('ND','North Dakota'),('OH','Ohio'),
 ('OK','Oklahoma'),('OR','Oregon'),('PA','Pennsylvania'),('RI','Rhode Island'),
 ('SC','South Carolina'),('SD','South Dakota'),('TN','Tennessee'),('TX','Texas'),
 ('UT','Utah'),('VT','Vermont'),('VA','Virginia'),('WA','Washington'),
 ('WV','West Virginia'),('WI','Wisconsin'),('WY','Wyoming'),
 ('PR','Puerto Rico'),('VI','US Virgin Islands'),('GU','Guam'),
 ('AS','American Samoa'),('MP','Northern Mariana Islands')
on conflict (code) do update set name = excluded.name;


-- serviceable_countries is intentionally NOT seeded here. EDGAR encodes
-- foreign locations with its own two-character code list, so 02_route.py
-- prints the distinct non-US values actually present in the pull, they are
-- mapped by hand, and the table is seeded from that. The route script fails
-- loudly if this table is empty.
