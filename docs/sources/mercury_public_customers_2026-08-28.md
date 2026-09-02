# Primary-source evidence: Mercury's publicly named customers, captured 2026-08-28

Harvested to seed a **suppression table**. Mercury claims "1 in 3 Startups choose Mercury", and the
homepage footnote scopes that to "US-based companies that received an angel, pre-seed, seed, or
Series A investment reported on Crunchbase in the most recent year", which is very close to the
population a Form D pull produces. No external data source identifies which leads already bank with
Mercury (see `docs/verification_log.md`, open item B1). These are the only names the seller
publishes.

Re-capture command, run against every solutions and product page in the site nav:

```bash
curl -s -L -A "Mozilla/5.0" https://mercury.com/<page>
```

Extraction: strip `<script>`/`<style>`, convert tags to newlines, collapse whitespace, then take
each testimonial attribution line and the name line preceding it. Five attributions place the
company on the following line and were resolved individually.

**Coverage, stated honestly: 35 companies against a claimed 300,000 customers, so roughly 0.01%.**
This table is not a solution to B1. It is the seeded starting state of the object that solves B1 in
production, which is a CRM-populated suppression list.

---

## The table

| # | Company | Person | Role | Source page |
|---|---|---|---|---|
| 1 | Ways & Means | Karen Halstead | Founder | `/`, `/agencies-and-consultants` |
| 2 | Linear | Karri Saarinen | Founder | `/` |
| 3 | Supabase | Paul Copplestone | Founder and CEO | `/` |
| 4 | Freedom Biosciences | Dina Burkitbayeva | CEO | `/business-banking`, `/life-science` |
| 5 | Common Paper | Jake Stein | Co-founder & CEO | `/business-banking` |
| 6 | Manta Sleep | Mark Zhang | CEO | `/business-banking`, `/ecommerce` |
| 7 | **Spacecadet Ventures** | Wiz Abdullah | Co-founder & Partner | `/vc-funds` |
| 8 | **2048 Ventures** | Zann Ali | Partner | `/vc-funds` |
| 9 | Minaal | Jimmy Hayes | Co-founder | `/ecommerce` |
| 10 | Raide | Kyle Siegel | Founder | `/ecommerce` |
| 11 | The Lab IT | Pablo Beltran | Founder & Consultant | `/agencies-and-consultants` |
| 12 | Phantom | Brandon Millman | CEO | `/crypto` |
| 13 | CoinTracker | Chandan Lodha | Co-founder | `/crypto` |
| 14 | XMTP | Matt Galligan | Founder | `/crypto` |
| 15 | TwoStep Therapeutics | Caitlyn Lee Miller, PhD | CEO | `/life-science` |
| 16 | Lactiga | Viraj Mane, PhD | Co-founder & CSO | `/life-science` |
| 17 | Infinimmune | Wyatt J. McDonnell, PhD | Co-founder & CEO | `/life-science` |
| 18 | Patch | Brennan Spellacy | Co-founder & CEO | `/climate` |
| 19 | Zeno Power | Jonathan Segal | Co-founder & COO | `/climate` |
| 20 | Renuble | Tinia Pina | Founder & CEO | `/climate` |
| 21 | IBEX Consulting | Christopher Millard | CEO | `/accounting-firms` |
| 22 | Ignite Spot Accounting | Dan Luthi | Partner | `/accounting-firms` |
| 23 | Acuity | Kenji Kuramoto | Founder | `/accounting-firms` |
| 24 | Yogi CPA | Zunie Nguyen | Founder & CEO | `/accounting-firms` |
| 25 | Assort Health | Jon Wang | Co-CEO | `/healthcare-services` |
| 26 | Mochi Health | Myra Ahmad | CEO | `/healthcare-services` |
| 27 | Poetry Camera | Kelin Carolyn Zhang | Co-founder | `/llc-banking` |
| 28 | Buried Wins | Drew Giovannoli | Founder | `/llc-banking` |
| 29 | KindDesigns | Anya Freeman | CEO | `/real-estate-and-construction` |
| 30 | Blue Maple Rentals | Tony Cappaert | Founder | `/real-estate-and-construction` |
| 31 | Mona | Andrew Leon Hanna | Founder | `/saas` |
| 32 | Sprig | Ryan Glasgow | CEO | `/saas` |
| 33 | Alma | Aizada Marat | Co-founder & CEO | `/invoicing` |
| 34 | Wimp Decaf Coffee Co. | Matthew Smith | Founder | `/invoicing` |
| 35 | MasterCare LLC | Nathan Sanow | President | `/invoicing` |

Also named, with no company attached: **James Beshara**, angel investor, `/vc-funds`. Recorded but
not a suppression row, since suppression keys on the organisation.

---

## Why the domain column is deliberately absent

The spine keys identity on **normalised root domain**, so a suppression table needs domains. They
are **not** written here, because guessing `supabase.com` from the string "Supabase" is exactly the
inference this archive exists to prevent, and five of these names are ambiguous as domains
(Acuity, Patch, Alma, Mona, Raide).

**The suppression list is resolved by the same Clay waterfall the leads go through.** That is not a
workaround, it is the better design and a genuine demo beat: the resolver is dogfooded on a set
where the right answer can be eyeballed, which produces a free accuracy check on the resolver
itself before a single lead is enriched.

## Two facts this capture adds

1. **Mercury publishes VC funds as customers**: Spacecadet Ventures and 2048 Ventures. Further
   confirmation of `docs/verification_log.md` #25: funds are customers, not an excluded class.
2. **Real Estate & Construction has its own page with its own testimonials.** Third independent
   confirmation that correction #6 was wrong and #22 correctly withdrew it.
