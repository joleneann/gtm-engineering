**INTRODUCTION**

Mercury sells banking and finance operations to startups. This Go-to-Market Engineering build aims to acquire new customers for Mercury by sending them a cold email when they raise funding.

The build demonstrates system design, data modelling, edge case handling, schema design, ICP segmentation, scoring logic, and copywriting at scale. Python ingests and scores leads; Supabase is the truth layer; Clay for enrichment; n8n is the conveyor belt, and Pipedrive is the CRM. I built this with Claude Code, held to a written contract in CLAUDE.md: it wrote the scripts; I made every design call.

**THE TRIGGER**

I got the idea to look at a funding event from Mercury’s homepage, which declares 1 in 3 startups as their customers - defining startups as entities reporting funding upto Series A on Crunchbase in the past year.

Since Mercury defines its market as companies that just raised, I needed the best possible feed of that event, which, after considering several options, is the SEC Form D. 

**Several reasons make Form D the best trigger** 

* **A relevant event**: a raise reopens the business banking question  
* **Constant pipeline**: arrives every working day  
* **Comprehensive dataset**: must be filed by all companies raising private capital within 15 days of sale  
* **Information density**: company name, industry, officers, address, and phone all non-optional in the filing  
* **Free and machine-readable**: SEC EDGAR is a public REST API 

**10 rejected alternatives**

| Source | Why not |
| :---- | :---- |
| SEC Form 1-A | A halfway house between a private raise and a stock market listing: the company sells shares to the general public. Few filings + filing before the money arrives rather than after, so it is not a cash event. |
| 8-K, S-1, 10-Q | Public-company events. Those companies already have treasury desks and banking relationships. Wrong ICP entirely. |
| Crunchbase, PitchBook, Tracxn, Harmonic | Expensive and derivative: substantially built from Form D plus press, with a delay. |
| TechCrunch, Google News, Funding RSS | PR coverage skewing big and consumer. Amounts are often unclear, nobody is named, duplication of coverage across outlets |
| Job postings/hiring spikes | Lags by months, carries no amount, and needs scraping |
| Y Combinator / Techstars batches | Two batches a year gives no continuous pipeline. |
| State incorporation filings | Registering a company is not raising money. There is no cash and nothing to score. |
| LinkedIn headcount growth | Needs scraping. It also lags the raise and never tells you the amount. |
| USPTO trademark filings | Filing a trademark says little about whether a company just raised. |
| Product Hunt/ launch feeds | Launching a product is not a money event. |

**Shortcomings**  
US incorporated companies that don’t raise under Regulation D - crowdfunded, bootstrapped, and revenue-financed companies could be great candidates for Mercury, but an alternative pathway had to be built to find them, which is out of scope for this build. 

**PULLING AND STORING DATA**

Python scripts use the REST endpoints from the EDGAR SEC database system to fetch

* The daily filing index, which has form type in the first column. This helps the system only pull Form Ds, which we need  
* Each Form D of the day in XML  
* Each company’s filing history in JSON

These become 2 Supabase tables:

1. **filings_raw** for all filings with date, keyed on accession number plus CIK - a compound key, as several companies can be listed in one filing if they sell in the same transaction  
2. **entities_raw** keyed on CIK

Both tables are upserted, so any re-run is safe and produces no duplicates. Storing the documents whole rather than the fields the model currently uses means a field ruled out today can be refactored tomorrow if the scoring system changes, without a refetch of the documents.

Two things inside a filing repeat and cannot be a single column, so they get child tables joined on (accession_number, cik): **filing_related_persons** (median 2 people per filing, max 15) and **filing_former_names**.

**Three Route Outs**

**1. Routing out Funds**

Form D is filed by funds as well as by operating companies, and this build only caters to companies. Funds are routed out by looking at the values of 2 filing fields catches most of them.

* industry group set to ‘Pooled Investment Fund’, or  
* the pooled-fund tick in the securities offered

Using either one of the two caused leaks.

They move to table **formd_funds** as Mercury advertises funds as one of their customer segments. A separate flow can be built for them later as it requires different scoring logic and copy.

**2. Routing out Unserviceable Companies**

Mercury serves companies incorporated in the USA and physically located in 1 of 12 countries (US, UK, Canada, India, Singapore, Israel, Netherlands, Spain, Germany, Denmark, Australia or, Mexico)

As filing addresses can sometimes be those of firms or agencies, we primarily read the business addresses from the company history that is required to be kept current with the SEC, and the filing only when history doesn’t have an address (about 6% of companies in the demo sample), even tho it carries some risk of accepting non-eligible companies.

Failing rows are routed out to the table **likely_unserviceable_companies,** which specifies if they failed on jurisdiction of incorporation or business address. (jurisdiction_fail and/or address_fail)

EDGAR writes countries as its own two-character codes. Each code was looked up against EDGAR's published list, and the eligible country codes are stored in the **serviceable_countries** table. 

**3. Parking companies with no scorable industry**

A share of the remaining companies select ‘Other’ as their industry group, which our scoring system cannot use. 

In production, I'd send these companies to Clay for industry enrichment and have them come back to Supabase for scoring. For now, they are parked in **no_industry_companies**.

Remaining companies go to **outbound_companies_unscored** for scoring.

**SCORING**

The scoring model I designed for this demo is simple with 4 inputs, totaling 10 points upto 2 decimal places, upon which a company’s score is determined.  
Scoring parameters had to be taken from fields which were reliably 100% coverage in the data.

| Input | Max | Source | Direction | Shape |
| :---- | :---- | :---- | :---- | :---- |
| Amount Sold | 5.00 | Form D | higher is better | log curve between Mercury's own form boundaries |
| Amount Remaining | 1.00 | Form D | lower is better | same curve inverted |
| Industry | 3.00 | Form D | ranked table match | seeded assumptions |
| Prior Form D filings | 1.00 | History | fewer is better | banded by test cases |

Going deeper into each

**Amount Sold, 5 Points**

Points = 5 × log10(1 + sold / 100_000) / log10(501), capped at 5.00

Count the raise in units of $100,000, take the log, and scale so $50M and above lands on 5. The +1 is what lets a company that sold nothing score exactly zero.

| Raise in $ | Points |
| :---- | :---- |
| 0 | 0.00 |
| 50,000 | 0.33 |
| 100,000 | 0.56 |
| 250,000 | 1.01 |
| 1,000,000 | 1.93 |
| 10,000,000 | 3.71 |
| 25,000,000 | 4.44 |
| 50,000,000 | 5.00 |

This is a proxy for the cash a company has on hand at the moment in time of the filing.

Log, because three of the seller's four boundaries are powers of ten. Mercury's inbound form makes every prospect pick from 5 expected balance bands bounded at $100k, $1m, $10m and $50m, and the first three are 10⁵, 10⁶ and 10⁷: each band ten times the last. A seller that widens its buckets by a constant multiple is thinking about money logarithmically. 

My first instinct was to let the data decide and let each day’s filings set their own percentiles but company score will constantly shift and make the system hard to maintain.

Multiple filings by one company

If a company makes 2 or more distinct filings within a rolling 12 months of their first filing in the system, and before they become a customer, that number is added together in this build. Dedupe on the fingerprint of the offering itself (totalOfferingAmount, totalAmountSold, dateOfFirstSale, totalNumberAlreadyInvested), then add the amounts.

Both amounts are added: totalAmountSold and totalRemaining.  
Non-amount fields (industry, contact, related persons, filing date) come from the newest filing.

A company filing again will reenter the pipeline, as a new raise is a new reason to write to them. Whether we actually write to them or not is determined later in the flow, deduping them against existing and inbound customers.

In production, existing and inbound customer tables come from the CRM and will also contain companies a rep put on hold, closed or lost.

**Total Remaining, 1 Point**

The same curve as amount, inverted.

curve(v) = log10(1 + v / 100_000) / log10(501), capped at 1  
points   = 1 - curve(v)

| Raise in $ | Points |
| :---- | :---- |
| 0 | 1.00 |
| 100,000 | 0.89 |
| 1,000,000 | 0.61 |
| 10,000,000 | 0.26 |
| 50,000,000+ | 0.00 |

One point is the amount left to raise, and it exists to catch companies in the right industry that declared a large offering and have sold none of it. It also adds separation; adding it leaves the model with materially fewer tie groups than amount sold produces on its own.

The assumption is that a company with most of its round closed is closer to making a banking decision. It gets one point rather than more because its correlation with amount points is about +0.3 on test cases, so it is a weaker second reading of something amount already measures rather than an independent signal.

Zero left to raise lands on exactly 1.00. 

**Industry Match, 3 points**

[https://www.sec.gov/files/formd.pdf](https://www.sec.gov/files/formd.pdf)

| Group | SEC Filing Code | Points |
| ----- | ----- | ----- |
| Technology | Other Technology | 3.00 |
| Technology | Computers | 3.00 |
| Health Care | Biotechnology | 2.70 |
| Health Care | Pharmaceuticals | 2.70 |
| Business Services | Business Services | 2.55 |
| Health Care | Other Health Care | 2.40 |
| Health Care | Health Insurance | 2.40 |
| Health Care | Hospitals and Physicians | 2.40 |
| Energy | Other Energy | 2.25 |
| Energy | Energy Conservation | 2.25 |
| Energy | Environmental Services | 2.25 |
| Energy | Electric Utilities | 2.25 |
| Technology | Telecommunications | 2.10 |
| Retailing | Retailing | 1.80 |
| Banking & Financial Services | Other Banking and Financial Services | 1.50 |
| Real Estate | Commercial | 1.20 |
| Real Estate | Residential | 1.20 |
| Real Estate | Construction | 1.20 |
| Real Estate | REITS and Finance | 1.20 |
| Real Estate | Other Real Estate | 1.20 |
| Manufacturing | Manufacturing | 0.90 |
| Agriculture | Agriculture | 0.90 |
| Restaurants | Restaurants | 0.90 |
| Travel | Airlines and Airports | 0.60 |
| Travel | Lodging and Conventions | 0.60 |
| Travel | Tourism and Travel Services | 0.60 |
| Travel | Other Travel | 0.60 |
| Energy | Oil and Gas | 0.30 |
| Energy | Coal Mining | 0.30 |
| Banking & Financial Services | Investing | 0.30 |
| Banking & Financial Services | Commercial Banking | 0.30 |
| Banking & Financial Services | Investment Banking | 0.30 |
| Banking & Financial Services | Insurance | 0.30 |

The next three points go to industry suitability.  
In production, Mercury companies will be coded according to the SEC’s filing codes and ordered by lifetime value.   
For the demo, I assumed and seeded LTV.

**Prior Form D Filings, 1 point**

| Prior Filings | Points |
| :---- | :---- |
| 0 | 1.00 |
| 1 | 0.75 |
| 2 | 0.50 |
| 3 or 4 | 0.25 |
| 5 or more | 0.00 |

I’ve assumed the business banking question would already have been settled with more filings, so more filings score lower.  
Measured as a count of total Form D’s filed minus the number of Form Ds rolled into the current row.

**Scoring factor I’ll consider adding in prod**

* Check internal data on the average conversion time of companies by industry. This would help assign a time window per industry within which outreach should be intensified, as the likelihood of conversion is higher. This would help further prioritise leads and staff for this function.

**mill_list** stores addresses and phone numbers appearing for 3+ CIKs - these are suspected agencies and mills filing on behalf of companies. They are removed before the enrichment step, so that the right candidate addresses and phone numbers can be sent.

**CLAY PAYLOAD**

Scored companies sit in **outbound_companies_scored** with date of filing, all scoring factors, the final score, and the following parameters, ready to be sent to Clay for enrichment

IDX = Filing Index, XML = Filing, JSON = Company History

Because people read these columns left to right in a Clay table, the column order follows the workflow: the key and priority, then who and what to search for with evidence to use, then the facts the copy is built from.

| # | Clay Row Name | Source | Purpose |
| ----- | ----- | ----- | ----- |
| 1 | cik | IDX | Company key |
| 2 | score | **outbound_companies_scored** | Prioritising companies |
| 3 | current_name | XML entity name + JSON name (deduped) | Enrichment |
| 4 | former_names | XML previous names + JSON former names (deduped) | Enrichment |
| 5 | contact_name_designation | XML signer plus title. Blank if attorney or authorised person/representative | Company contact person + Enrichment |
| 6 | also_signed_for | **signer_list** | Other companies this one person signed for, so 1 person gets one email |
| 7 | people | XML related persons first name + last name + relationship, excluding whoever is in contact_name | Enrichment |
| 8 | address_candidates | XML issuer street, city, state, zipcode + JSON street, city, state, country, zipcode. Deduped against **mill_list**. Strip punctuation, expand street types, map state to 2-letter code | Enrichment |
| 9 | phone_candidates | XML issuer phone number and JSON phone, digits only with the country code first. Deduped on **mill_list**. Keep both if different | Enrichment |
| 10 | industry | XML industry group type |  |
| 11 | amount_sold | XML |  |
| 12 | rolled_filing_count | Computed | How many Form D filings were added together to produce amount_sold |
| 13 | filing_date | IDX |  |

**Additional notes**

* people never repeat contact_name. Matching is on first and last name, lowercased, with honorifics and single-letter initials dropped  
* Two names that share a surname are not merged  
* people is stored as JSON and sent to Clay as one plain-text column. Supabase keeps it structured because the truth layer is SQL   
* contact_name is blanked when the signer is not the company's own officer, on two tests; the filing's authorizedRepresentative flag being true blanks it outright. Otherwise, the free-text signatureTitle is matched against the agent vocabulary: attorney, attorney-in-fact, power of attorney, authorised person, authorised representative, authorised signatory, authorised signer, filing agent, registered agent.  
* Where contact_name was blanked as an agent, people stays complete, because it is then the only place a human is named.  
* Phones leave in one written format: digits only, country code first, nothing else.   
* Block capitals are calmed when the payload row is built.   
* A person is written to once. Not once per company they signed for, hence the also_signed_for column in the Clay table. **signer_list** counts how many distinct companies each signer covers, built exactly as **mill_list**.   
* Every address ever written to is recorded in **contacted_emails**, keyed on the address rather than the company, because the thing being protected is a person's inbox and it must outlive the run, the company, and the campaign. It is checked in the same pass as the existing-customer and inbound joins, and a match exits dupe_already_emailed.   
* For **mill_list**, the value is an agency only when more than three distinct companies use it. Membership is counted on distinct CIK. occurrence_count is still recorded next to distinct_cik_count, because the pair is what separates a shared filing agent from a company that simply files often.

**ENRICHMENT AND COPY**

Clay resolves each company that lands to

* the company domain  
* work email of the primary contact, and   
* the copy for the email

**Domain**

* Clay’s waterfall enrichment in any order was clearly insufficient to determine the domain from the legal name and produced a lot of mistakes  
* I used Claygent, giving it multiple corroboration candidates like the company’s current and former legal names, personnel, address, and phone number candidates  
* I asked it to return evidence, reasoning, and a confidence score along with rejected candidates for transparency.  
* This produced correct domain names for all the test rows

**Work Email**

* 13 of 16 work emails were found by inputting domain name, contact name, and designation  
* ZeroBounce on these emails produced a +80% validity rate

**Copy**

* This step took some time and effort on prompt shapes and models  
* I was finally able to obtain decent copy by giving Claude Sonnet a tight sentence-by-sentence email structure where  
  * The first sentence used the company website and industry to observe how financial operations work within the company  
  * The second sentence spoke about how Mercury makes FinOps easier and uses amount_raised as a proxy for cash on hand to explicate Mercury’s relevant benefits  
  * Finally, it directs them to a demo and asks them to respond to the email if they’re interested in coming on board

**POST ENRICHMENT DEDUPE**

Enriched data comes back to Supabase to be deduped against three tables

1. **existing_mercury_customers** which, as the name suggests, lists existing Mercury customers  
2. **mercury_inbound**, which has information of the customers who have inquired on the website  
3. **contacted_emails,** which has all the emails of people contacted by the campaign so far

In production, given the volume of customers Mercury already has and the amount of inbound it likely receives, it could get expensive to enrich companies that are later found not to be campaign candidates.

One solution could be maintaining a record of legal names (via bank records) and CIK numbers via SEC records for existing customers, and CIK numbers for inbound customers to dedupe before they get enriched.

For the demo, we seeded one enriched customer for each and all fired.

**LOGGING PROGRESS WITH N8N**

n8n comes in after the dedupe.

**1. Sending Emails**

Once per company, the workflow asks the Supabase table **outbound_companies_scored** for records where enrichment_status is enriched, dedupe_status is unique, copy_body is not null, and pipedrive_deal_id is null.  
For each one it creates three things in Pipedrive: the organization, the person, and a deal parked at the Enriched stage. 

The deal is titled "Company name, Form D 2026-08-14", valued at the amount sold in USD, and carries the filing date, the score, and the drafted subject and body in custom fields.

Then it immediately writes those three Pipedrive IDs back into the Supabase table, into pipedrive_org_id, pipedrive_person_id and pipedrive_deal_id on the same row, keyed on the company's CIK, along with pipedrive_synced_at and a crm_stage of enriched. 

Then it forks on one question: is is_test_row true?

A real company goes down the bottom branch. It creates a Pipedrive activity of type task called "Draft ready, do not send", linked to the deal, the person and the organization, with the subject and body pasted into the note. The deal stays at Enriched. Nothing is sent. 

A test row goes up the top branch, and gets asked a second question: does work_email exactly equal the test address? If it passes, the email is sent, we sent two emails for the demo. Pipedrive deal moves to emaled stage and Supabase logs sent_at and a crm_stage of emailed, and the address is written to contacted_emails in lowercase.

**2. Catching Replies**

When someone replies to a cold email, this flow moves the deal on Pipedrive to Replied.

In production, you would not poll a mailbox: the sending platform pushes a webhook the moment a reply lands. If the sender matches a row already at crm_stage emailed on **outbound_companies_scored**, the deal moves to Replied on Pipedrive, then replied_at and crm_stage are written back to **outbound_companies_scored**. 

**CRM STRUCTURE**

HubSpot has no free trial without a work email ID, so I chose Pipedrive.

**Objects**

Three per company: Organization is the company, Person is the human who gets the email, Deal is the raise. 

One of each per company, because each company has exactly one row in Supabase and GTME 1 only picks up rows with no Deal yet. A company that raises again before becoming a customer does not get a second Deal: step 04 sums both raises into one row inside a 365-day window and records how many filings were added, so what reaches Pipedrive is one company, one Deal, one figure.

**The objects**

Each company gets one of each: Organization is the company, Person is the human who gets the email, Deal is the raise. 

**The stages**

Enriched, Emailed, Replied, Held, Closed Won, Closed Lost. Every Deal is created at Enriched, meaning it has a validated work email and written copy.

Held, Closed Won and Closed Lost are set by the person working the deal, not by the pipeline.

**REPORTING**

Campaign health is read from SQL views

* **v_funnel** for the pipeline  
* **v_outreach** for the CRM leg  
* **v_score_distribution** to see how well the scoring system works and if it gives enough separation of companies

In production, the EDGAR pull runs on a cron. Later, layer on cold calling and email sequences.

