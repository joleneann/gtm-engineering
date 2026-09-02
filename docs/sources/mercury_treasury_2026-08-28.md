# Primary-source evidence: Mercury, captured 2026-08-28

Every line below is verbatim from Mercury's own raw HTML, fetched with `curl` on 2026-08-28 from
<https://mercury.com/treasury>, <https://mercury.com/> and <https://mercury.com/business-banking>.
Nothing here passed through a page summariser. `docs/mercury_offer.md` is the interpretation; this
file is the record it must agree with.

Machine-readable companion: `docs/sources/mercury_site_constants_2026-08-28.json`, the site-wide
constants block embedded in every Mercury page.

Re-capture command:

```bash
curl -s -L -A "Mozilla/5.0" https://mercury.com/treasury \
  | sed -e 's/<[^>]*>/ /g' | sed 's/\\"/"/g' | tr -s ' \n' '  ' > mercury_treasury.txt
```

---

## A. The site constants block (authoritative, machine-readable)

Present identically on `/treasury`, `/business-banking` and a 404 page, so it is global site config
rather than page copy.

| Constant | Value | Stamped |
|---|---|---|
| `TREASURY_MINIMUM_ELIGIBLE_BALANCE_DOLLARS` | `$250,000` | |
| `TREASURY_APY` | `3.64` | 2026-07-31 |
| `MRGXX_APY_AT_60_BPS_FEE_TIER` | `3.12` | 2026-08-18 |
| `MRGXX_APY_AT_45_BPS_FEE_TIER` | `3.27` | |
| `MRGXX_APY_AT_35_BPS_FEE_TIER` | `3.37` | |
| `MRGXX_APY_AT_25_BPS_FEE_TIER` | `3.47` | |
| `MRGXX_APY_AT_15_BPS_FEE_TIER` | `3.57` | |
| `MCRYX_APY_AT_60_BPS_FEE_TIER` | `3.44` | 2026-08-21 |
| `MCRYX_APY_AT_45_BPS_FEE_TIER` | `3.59` | |
| `MCRYX_APY_AT_35_BPS_FEE_TIER` | `3.69` | |
| `MCRYX_APY_AT_25_BPS_FEE_TIER` | `3.79` | |
| `MCRYX_APY_AT_15_BPS_FEE_TIER` | `3.89` | |
| `JTCXX_APY_AT_60_BPS_FEE_TIER` → `_15_` | `3.03` → `3.48` | 2026-08-24 |
| `MULSX_APY_UPDATED_AT` | (ticker present, no APY values) | 2026-07-31 |
| **`BUSINESS_CHECKING_APY`** | **`0`** | **2026-08-27** |
| **`BUSINESS_SAVINGS_APY`** | **`0.001`** | **2026-08-27** |
| `PERSONAL_CHECKING_APY` | `0.001` | 2025-09-15 |
| `PERSONAL_SAVINGS_APY` | `3.25` | 2026-06-15 |
| `CUSTOMER_COUNT` | `300,000` | |

**Three findings that only exist in this block:**

1. **The fee tiers are named in basis points: 15, 25, 35, 45, 60.** The best yield sits at the
   **15 bps** tier and the worst at **60 bps**, which settles the fee direction outright: the fee
   **falls** as balances grow. No prose on the page states this.
2. **`BUSINESS_CHECKING_APY` is `0`**, stamped 2026-08-27. Business savings is `0.001`. Idle cash in
   a Mercury business account earns effectively nothing. This is the actual premise of the pitch.
3. **Two more fund tickers exist**, `JTCXX` and `MULSX`, alongside `MRGXX` and `MCRYX`. The page
   carries `data-page-variant: "treasury-mcryx-jtcxx"`, so **Mercury A/B tests the fund line-up**
   and the visible fund list is not stable. `JTCXX` is not identified anywhere in the visible copy;
   do not name a fund in copy without re-checking.

---

## B. `/treasury`, verbatim

**Minimum balance, three separate statements:**

> "Qualify for Mercury Treasury with a minimum balance of $250K across your Mercury accounts."

> "They meet the minimum balance requirement of $250,000 across all Mercury accounts"

> "Is there a minimum balance requirement for Mercury Treasury? Mercury Treasury is currently
> available to users with account balances over $250,000 across all Mercury accounts. We hope to
> open Mercury Treasury to all users in the future."

**Fees, both statements. Neither states a direction:**

> "What does Mercury Treasury cost? There are no fees to open an account or transact with Mercury
> Treasury."

> "Users are charged a small percentage of their total monthly Mercury Treasury positions at a rate
> determined by the total deposits held across all your Mercury accounts, ranging from 0.15% to
> 0.6%."

> "Treasury accounts carry an annual fee of 0.15%-0.60% based on total Mercury balances."

> "Yield and fee caps are represented as annualized numbers. Mercury Treasury, by Mercury Advisory,
> LLC, an SEC-registered investment adviser, seeks to earn net returns up to 3.89% annually on your
> idle cash for Mercury deposit sizes over $20M. Net yield numbers as of 08/21/2026. Mercury
> Treasury Solutions with Morgan Stanley has a separate fee structure."

**Eligibility:**

> "...located in one of the following countries: United States, United Kingdom, Canada, India,
> Singapore, Israel, Netherlands, Spain, Germany, Denmark, Australia, or Mexico. They meet the
> minimum balance requirement of $250,000 across all Mercury accounts. Unfortunately, we cannot
> support businesses that meet any of the following criteria at this time: LLCs taxed as sole
> proprietorships. Nonprofits or other 501(c)(3)..."

**The funds:**

> "Customize your portfolio across top-tier funds only available through Mercury. The State Street
> Institutional U.S. Government Money Market Fund: Mercury Class invests in U.S. Treasury bills,
> government agency debt, and repurchase agreements backed by U.S. government securities. The
> Morgan Stanley Ultra-Short Strategy Portfolio: Mercury Class is a mutual fund that invests in
> highly-liquid instruments such as commercial paper and Certificates of Deposit. It carries the
> highest Fitch rating for underlying credit quality and very low sensitivity to ma[rket]..."

**Liquidity:**

> "Money invested in the State Street Institutional U.S. Government Money Market Fund is available
> the same day if the transfer is initiated by 3pm ET, subject to partner processing times. Money
> invested in the Morgan Stanley Ultra-Short Strategy Portfolio will be avail[able]..."

**Custody:**

> "Your Mercury Treasury account is held in your name with our partner, Apex Clearing Corp. Apex
> Clearing Corp maintains a detailed record of each Treasury customer's holdings and is prohibited
> from using any of these funds or securities for its own purposes, and from commingling them with
> its own customers' holdings."

> "Mercury Treasury investments are held at Apex Clearing Corp, which is insured by the Securities
> Investor Protection Corporation (SIPC). In the unlikely event that Apex becomes insolvent, SIPC
> will insure customers up to $500K in securities and cash."

> "...with maximum protection for cash of $250,000 and $250,000 in investments."

**The $25M tier:**

> "Mercury Treasury Solutions with Morgan Stanley is currently available to Mercury account holders
> that have account balances exceeding $25M. Reach out to rm@mercury.com or contact your personal
> [relationship manager]..."

> "Mercury Advisory, LLC for entity clients with $25M+ balances. Portfolios are advised by Morgan
> Stanley. Mercury Advisory does not directly manage assets, but receives a referral fee. Please
> review all website information and fund prospectuses before investing."

---

## B1. The `/treasury` page body, complete and verbatim

### Hero

> **Maximize your money and your liquidity.**
> Earn up to 3.89% yield with lower-risk portfolios and same-day access to your money.
> **Exclusively for Mercury account holders.**
>
> [Enter your email] → **Open account** | **Contact sales**
>
> Mercury will occasionally send you emails with offers, news, and promotions. Check this box if
> you do not want to receive them. [Opt out]
>
> Mercury Treasury accounts are offered by Mercury Advisory LLC, an SEC-registered investment
> adviser.

**"Exclusively for Mercury account holders" is the most consequential line on the page** and was
missed by two earlier passes. It is analysed in `docs/mercury_offer.md` section 3b.

**Two CTAs, not one.** "Open account" and "Contact sales" sit side by side, which is the $25M lane
split expressed in the page's own UI: self-serve below, sales-assisted above.

### Four value propositions

> **Strategic cash management made simple** — [Explore demo]
>
> - **Effortlessly earn up to 3.89%** — Qualify for Mercury Treasury with a minimum balance of
>   $250K across your Mercury accounts.
> - **Access your capital any time** — Get the flexibility you need with withdrawals as soon as
>   same day.
> - **Automate your cash management** — Set custom auto-transfers between your operating and
>   investment accounts.
> - **Secure your runway** — Your money is invested in lower-risk mutual funds held in your name.

An interactive **"Explore demo"** exists on the page and is usable as a CTA asset in copy: it is a
lower-commitment ask than "open an account".

### The funds

> **Growth for the long term, flexibility in the short term**
> Customize your portfolio across **top-tier funds only available through Mercury**
>
> - The State Street Institutional U.S. Government Money Market Fund: **Mercury Class** invests in
>   U.S. Treasury bills, government agency debt, and repurchase agreements backed by U.S.
>   government securities
> - The Morgan Stanley Ultra-Short Strategy Portfolio: **Mercury Class** invests in commercial paper
>   and certificates of deposit and carries the highest Fitch rating
>
> Personalized portfolio management services are available for customers with $25M in Mercury
> balances

**"Only available through Mercury"**, plus the "Mercury Class" share class on both funds, is a
competitive claim not previously recorded: these specific share classes are not obtainable
elsewhere. Treat the exclusivity claim as Mercury's own marketing, not as verified fact.

### Automation and liquidity sections

> **Put your cash management strategy on cruise control with automated transfers**
>
> "Mercury has made the process of transferring funds between a high-yield Treasury account and a
> checking account remarkably seamless, ensuring we make the most of every dollar."
> — **Amaro Luna, Co-founder, Telegraph**
>
> **Unlock high yields without locking up your money**
> Unlike other high-yield investments, your money is always within reach with Mercury Treasury. You
> can easily transfer funds to your checking account as soon as same day.

### The yield table, with its own headers

> **Earn up to 3.89% yield. No surprise fees.**
> Yield (net of fees) up to:

| Total Mercury Deposits | Government Money Market (MRGXX) — **Same-day liquidity** | Ultra-Short Term Bonds (MCRYX) — **1-2 day liquidity** |
|---|---|---|
| > $50M | **Contact us** | **Contact us** |
| $20-$50M | 3.57% | 3.89% |
| $10-$20M | 3.47% | 3.79% |
| $5-$10M | 3.37% | 3.69% |
| $2-$5M | 3.27% | 3.59% |
| $250K-$2M | 3.12% | 3.44% |

Two things the earlier capture of this table lost: **liquidity is a column header**, so the page
itself frames the choice as yield-versus-access rather than yield alone; and **above $50M the answer
is "Contact us"**, a third sales-assisted band above the $25M one.

---

## B2. The `/treasury` FAQ block, complete and verbatim

Reproduced in full because the earlier capture quoted it only in fragments, and two of the gaps
mattered. Eight questions.

### Is my business eligible for Mercury Treasury?

> Today, most businesses are eligible for Mercury Treasury if they meet **three requirements**:
>
> 1. **They are a U.S. entity**
> 2. They are **physically located** in one of the following countries: United States, United
>    Kingdom, Canada, India, Singapore, Israel, Netherlands, Spain, Germany, Denmark, Australia,
>    or Mexico
> 3. They meet the minimum balance requirement of $250,000 across all Mercury accounts
>
> Unfortunately, we cannot support businesses that meet any of the following criteria at this time:
>
> - LLCs taxed as sole proprietorships
> - Nonprofits or other 501(c)(3) organizations
> - Foreign financial institutions
> - Banks organized under foreign laws and located outside of the United States
> - Legal entity customers who are exempt from identifying and verifying beneficial owners
> - Certain registered and exempt investment advisers
> - Securities brokers or dealers
> - Businesses with a beneficial owner that has a home address in certain restricted countries
>
> We are working hard to make Mercury Treasury available to more businesses, so please check back
> regularly for the latest eligibility criteria.

**Requirements 1 and 2 are separate tests, and the build had them fused.** Being a U.S. entity is
not the same as being located in the U.S.: a Delaware C-corp operating out of London or Bangalore
satisfies both. See correction #17 in `docs/verification_log.md`.

**"Please check back regularly for the latest eligibility criteria"** is Mercury saying this list
moves. The gate is built against a dated capture, and the date has to be visible in the code.

### What does Mercury Treasury cost?

> - There are no fees to open an account or transact with Mercury Treasury.
> - Users are charged a small percentage of their total monthly Mercury Treasury positions at a
>   rate determined by the total deposits held across all your Mercury accounts, ranging from
>   0.15% to 0.6%.
> - Yield and fee caps are represented as annualized numbers. Mercury Treasury, by Mercury
>   Advisory, LLC, an SEC-registered investment adviser, seeks to earn net returns up to 3.89%
>   annually on your idle cash **for Mercury deposit sizes over $20M**. Net yield numbers as of
>   08/21/2026.
> - Mercury Treasury Solutions with Morgan Stanley has a separate fee structure.
> - Please see important terms and conditions at the bottom of this page.

Note the headline 3.89% is explicitly conditioned on deposits **over $20M**, which is the 15 bps
fee tier. It is not the rate a $300K account receives; that account gets 3.44% on the same fund.

### Can I withdraw my funds immediately?

> Yes, you can withdraw money from your Mercury Treasury account at any time — the time it takes to
> transfer out will vary depending on which fund the money is invested in. Money invested in the
> State Street Institutional U.S. Government Money Market Fund is available **the same day if the
> transfer is initiated by 3pm ET**, subject to partner processing times. Money invested in the
> Morgan Stanley Ultra-Short Strategy Portfolio will be available as soon as **1-2 business days**
> later, but it can take **up to 4 business days**.

The earlier capture truncated this at "will be avail…". The full version matters for copy: the
highest-yield option is also the slowest to exit, which is the honest trade-off to lead with rather
than the yield number.

### Is my Mercury Treasury account held in my name?

> Your Mercury Treasury account is held in your name at our partner, Apex Clearing Corp, a
> FINRA-regulated broker-dealer that has been in business for **over 40 years**. This means that
> every time a customer signs up for Mercury Treasury, we open an account in their name at Apex,
> which holds their funds in custody. A few other things to note about Apex:
>
> - It maintains a detailed record of each Treasury customer's holdings and is prohibited from
>   using any of these funds or securities for its own purposes — or from commingling them with its
>   own customers' holdings.
> - It is regulated by the SEC and FINRA.
> - It is regularly audited and must publish its financial statements to the public.
> - It is required to keep excess capital on hand to ensure customer deposits are protected.
>
> We've worked with experienced regulatory counsel to set this up. **Regardless of what happens to
> Mercury**, any funds and securities held at Apex will remain safe and accessible.

### How are my funds in Treasury secured?

> Funds invested via Mercury Treasury are protected in several ways:
>
> - Your Mercury Treasury account is held in your name with our partner, Apex Clearing Corp. …
>   Because assets are held in your name, they remain available to be transferred to an account at
>   another broker in any of the following events:
>   - **Mercury** bankruptcy, financial instability, sale or acquisition
>   - **Apex** bankruptcy, financial instability, sale or acquisition
> - Apex is regulated by the SEC and FINRA, and is regularly audited and must publish financial
>   statements to the public. Apex is also required to keep excess capital on hand…
> - Mercury Treasury offers two mutual funds that invest in lower-risk, short-term debt securities,
>   such as Treasury bills, **municipal debt**, or corporate bonds…
>   - State Street Institutional U.S. Government Money Market Fund: Mercury Class invests in U.S.
>     Treasury bills, government agency debt, and repurchase agreements backed by U.S. government
>     securities.
>   - Morgan Stanley Ultra-Short Strategy Portfolio: Mercury Class is a mutual fund that invests in
>     highly-liquid instruments such as commercial paper and Certificates of Deposit. It carries the
>     highest Fitch rating for underlying credit quality and very low sensitivity to market risk.
> - Mercury Treasury accounts are covered by … SIPC … SIPC protects $500,000 worth of securities
>   and cash, with maximum protection for cash of $250,000 and $250,000 in investments.

**The insulation covers both Mercury and Apex failing, not just Mercury.** The earlier record said
only Mercury, which understated the strongest trust claim on the page.

### How is Mercury Treasury insured?

> Mercury Treasury investments are held at Apex Clearing Corp, which is insured by the Securities
> Investor Protection Corporation (SIPC). In the unlikely event that Apex becomes insolvent, SIPC
> will insure customers up to $500K in securities and cash.

### Is there a minimum balance requirement for Mercury Treasury?

> Mercury Treasury is currently available to users with account balances over $250,000 across all
> Mercury accounts. **We hope to open Mercury Treasury to all users in the future.**

### Is there a minimum balance requirement for Mercury Treasury Solutions with Morgan Stanley?

> Mercury Treasury Solutions with Morgan Stanley is currently available to Mercury account holders
> that have account balances exceeding $25M. Reach out to rm@mercury.com **or contact your personal
> relationship manager** for more details.

"Your personal relationship manager" confirms that $25M+ accounts already have a named human at
Mercury, which is why that tier is a different motion rather than a higher score.

### Fund prospectus links given on the page

- MRGXX: `https://www.ssga.com/us/en/institutional/resources/doc-viewer#mrgxx&prospectus`
- MCRYX: `https://morganstanley.prospectus-express.com/get_template.asp?clientid=morganstll&fundid=617455258&doctype=pros&template=`

---

## C. `/` (homepage), verbatim

> "300K+ Entrepreneurs love us. 1 in 3 Startups choose Mercury. $20B+ Monthly transaction volume.
> 4.9 Apple App Store rating"

Solution segments confirmed present in the raw markup: **SaaS, Ecommerce, Agencies, VC Funds,
Crypto, LLCs, Life Science, Accounting Firms, Climate, Healthcare Services.** ("Real Estate &
Construction" appeared in the summariser's output but was **not** confirmed in the raw grep; treat
as unverified.)

Named customers in raw markup: **Linear** (Karri Saarinen), **Gainful**, **Supabase**,
**Ways & Means**.

---

## D. `/business-banking`, verbatim

> "Get up to $5M in FDIC insurance through our partner banks and their use of sweep networks"

> "Treasury: Earn yield on idle cash right alongside your operating accounts."

> "Confidently scale your team with the IO Mastercard. Earn 1.5% cashback"

**No savings APY is advertised anywhere on this page.** Consistent with `BUSINESS_SAVINGS_APY:
0.001`.

---

## E. Third-party claims tested against the above

| Third-party claim | Source type | Verdict against primary source |
|---|---|---|
| Mercury Treasury pays ~3.7% "through a Dreyfus government cash management fund" | comparison blog | **False.** The string "Dreyfus" appears **zero** times across `/treasury`. The named funds are State Street MRGXX and Morgan Stanley MCRYX, with JTCXX and MULSX in the constants. |
| "Mercury pays up to 4% APY on the first $250,000 in its free savings feature" | comparison blog | **Not supported.** `BUSINESS_SAVINGS_APY` is `0.001`, stamped 2026-08-27, and `/business-banking` advertises no savings yield at all. |
| "Treasury requires $250K before you can access yield on idle cash" | comparison blog | **True**, confirmed three times on `/treasury`. |
| "monthly fee of 0.15% to 0.60% on balances" | comparison blog | **True**, and the constants additionally establish the direction the blog omits. |
| Arc quotes ~4.52% yield | comparison blog | **Untested.** Not checked against arc's own site. Do not put this number in copy without fetching joinarc.com directly on the day of use. |

**Standing conclusion:** the comparison blogs get the headline structure right and the fund
details wrong. They are usable as a pointer to what to check, never as a citation.

---

## F. `/switch-to-mercury`, verbatim — fetched 2026-08-28

Found via the nav link `"label":"Switch to Mercury","href":"/switch-to-mercury"` in the `/treasury`
markup. Not previously captured. It is Mercury's own answer to "why would I move my bank", and it
answers open item A4 in part.

```bash
curl -s -L -A "Mozilla/5.0" https://mercury.com/switch-to-mercury
```

Page description, from the embedded schema.org block:

> "Switching to Mercury is easier than you think. **No in-person visit, just four easy steps.**"

Hero:

> **Switch once. Get everything you need.**
> Banking, cards, expense management, payments, invoicing, and accounting in one place.
> - Replace fragmented financial tools
> - Get dedicated onboarding support
> - **Transition without disrupting operations**
> - Scale on a platform built for the long term
>
> [Enter your email] → **Open account** | **Talk to our team**

Testimonial:

> "We've used traditional banks, but they were painfully outdated. We've tried other fintechs, but
> they had serious glitches and shaky answers. That's why we're with Mercury — and why we're here
> to stay." — **Peer Richelsen, Co-founder and Chairman, Cal.com**

Product list, verbatim:

> - **Business banking** — Open checking and savings accounts **with no minimums**.
> - **Cards & expense management** — Issue cards, set controls, and manage spend in one place.
> - **Payments** — Send money and pay bills with no fees on USD payments.
> - **Invoicing** — Create and send branded invoices with no standalone AR tool.
> - **Accounting automations** — Sync with Quickbooks, Xero, or NetSuite.
> - **Mercury Treasury** — Put idle cash to work with Treasury options yielding up to 3.89%.

**The migration section, which is the answer to the switching-cost objection:**

> **Migrate with structure, not disruption.**
> - **Adopt processes on your timeline** — Start with the financial tasks that matter most —
>   operating accounts, cards, bill pay, or invoicing — and migrate others as you're ready.
> - **Get guided support** — Work with our implementation team to map your setup, move funds, and
>   ensure nothing is overlooked during the switch.
> - **Run accounts in parallel** — **Keep your existing bank active while you transition** payments
>   and deposits to Mercury, minimizing operational risk.
> - **Maintain clean accounting** — books stay complete, accurate, and reconciled throughout.

**Mercury vs "Legacy banks" comparison table, verbatim:**

| | Mercury | Legacy banks |
|---|---|---|
| Business checking & savings | Fast, online application | Limited |
| Monthly service, overdraft, minimum balance fees | **$0** | **$5–$35** |
| FDIC insurance | **Up to $5M** with partner banks' sweep networks | **$250K** |
| Free same-day ACH, domestic wires, USD international wires | yes | (not claimed) |
| Business credit cards | Uncapped **1.5% cashback on all** spend | 1%–5% on select purchases |
| Annual fees | **None** | Fees vary |
| Credit checks / personal guarantees | **None** | Some |
| Treasury and cash management | yes | Limited |

**The disclosure that must sit alongside any of the above:**

> "**Mercury is a fintech company, not an FDIC-insured bank.** Banking services provided through
> **Choice Financial Group and Column N.A.**, Members FDIC."

## G. Two lines on `/treasury` itself, missed by earlier passes

> "**Access an entire financial platform powered by your Mercury account** — Checking and savings
> accounts: **Secure up to $5M in FDIC insurance** through our partner banks and their sweep
> networks. IO credit card: Confidently scale your team…"

This matters for scope: **the $5M FDIC figure is on the Treasury page itself**, inside Mercury's own
Treasury pitch, not only on `/business-banking`. It is part of the Treasury offer as Mercury
presents it.

> "Realize your capital's full potential. **Apply online in 10 minutes or less.** [Open account]"

The stated cost of the switch, in Mercury's own words.

---

## H. `mercury.com` homepage, full body and all disclaimers — 2026-08-28

Supplied by the user as a full page paste. Section C of this file held only four homepage stat
lines; this is the complete page. **The disclaimer block at the foot is the highest-value part of
the entire evidence archive** and had never been read.

### Hero

> **Radically different banking**
> Apply online in **10 minutes** to experience banking unlike anything that's come before.
> [Enter your email] → **Open account** | **Launch demo**
>
> Mercury is a fintech company, not an FDIC-insured bank. Banking services provided through Choice
> Financial Group and Column N.A., Members FDIC.

### The four product blocks

> **Everything you do with money. All in one place.**
>
> - **Business banking & more** — Apply for **free checking and savings accounts with zero
>   minimums**, earn up to 3.89% yield with **Treasury by Mercury Advisory**, and access loans.
> - **Cards & expense management** — Earn 1.5% cashback on credit card spend…
> - **Payments & invoicing** — no fees on USD payments, free invoices…
> - **Accounting** — Sync with Quickbooks, Xero or NetSuite, AI-powered automations…

### Testimonials

> "Unlike most financial institutions, Mercury is built on software. Everything can be done within
> the app in 1-2 minutes." — **Karri Saarinen, Founder, Linear** (tagged **SaaS**)
>
> "Mercury has completely changed my expectations of what banking should do." — **Paul Copplestone,
> Founder and CEO, Supabase**

### Onboarding and fee claims

> **Get started fast. And never stop moving.**
> - **Apply online in 10 minutes** — Free checking and savings accounts, **no in-person visits or
>   paperwork**.
> - **Get a credit card instantly** — as soon as **day one, no minimums, credit checks, or personal
>   guarantees**.
> - Tackle banking tasks in seconds, universal search bar.
>
> **Stop losing money to fees. Start using it to fuel your growth.**
> - **$0** to send money in USD via wire, ACH, and real-time payment.
> - **1.5% cashback**, unlimited, automatically deposited, no points.
> - **Earn up to 3.89% yield with Mercury Treasury**: "Access high-liquidity, lower-risk portfolios
>   powered by **J.P. Morgan Asset Management and Morgan Stanley**"

**The fund lineup on the homepage is J.P. Morgan + Morgan Stanley. `/treasury` names State Street
(MRGXX) + Morgan Stanley (MCRYX).** The constants carry four tickers (MRGXX, MCRYX, JTCXX, MULSX)
for two visible slots. This confirms the standing caution: **Mercury A/B tests the fund line-up, so
fund names are not stable and must never be hardcoded into copy.**

### Scale claims

> **300K+** Entrepreneurs love us · **1 in 3** Startups choose Mercury · **$20B+** Monthly
> transaction volume · **4.9** Apple App Store rating

### The security section, which is the switching argument

> **Standard protection stops short. Mercury goes further.**
> - **20x the usual coverage**: Get up to **$5M FDIC insurance** through our partner banks and
>   their sweep networks to ensure eligible deposits are protected.
> - **Next-level account security**: fraud and phishing protection, passkeys, dark web monitoring.
> - **Controls at your fingertips**: approval flows, locks, permissions.

**"20x the usual coverage" is Mercury's own framing of the FDIC line**, and it sits on the homepage
as a top-level differentiator, not a footnote. See `docs/mercury_offer.md` section 6d.

### Closing CTAs and the paid tier

> **Banking, redesigned from the ground up.** [Open account] [Contact sales]
>
> - **Mercury for business**: "For **$0/month**, get started with business banking…" [Explore demo]
> - **Mercury for personal**: "**3.25% APY** on your savings account, joint accounts, unlimited
>   free USD wires" [Learn more]

### Footer: the full solutions list

> Ecommerce · Agencies, Consultants & Firms · SaaS · VC Funds · Crypto · LLCs · Life Science ·
> Accounting Firms · Climate · **Real Estate & Construction** · Healthcare Services

**"Real Estate & Construction" is real.** Correction #6 in `docs/verification_log.md` recorded it as
a summariser invention because it did not survive a grep of `/treasury`. It is in the homepage
footer nav. #6 was itself wrong; see correction #22.

Footer also names a resource page: **"Mercury Business Banking vs. Chase"**, a direct lead for the
legacy-bank baseline in open item A3.

---

### The disclaimer block, verbatim. Read this before writing any number.

**FDIC:**

> "Mercury is a fintech company, not an FDIC-insured bank. Banking services provided through Choice
> Financial Group and Column N.A., Members FDIC. **Deposit insurance covers the failure of an
> insured bank.** … Deposits in checking and savings accounts are FDIC-insured through Choice
> Financial Group and Column N.A. **and their Sweep Program Network Banks. Certain conditions must
> be satisfied for pass-through FDIC insurance to apply.**"

**The yield basis:**

> "Mercury Treasury earns up to 3.89% yield annually, based on the **30-day Effective Yield for
> MCRYX as of 08/21/2026**, and **assumes total Mercury deposits of $20M+**. Treasury accounts carry
> an annual fee of **0.15%–0.60% based on total Mercury balances**."

**The fee-waiver disclosure, which is the most important line in the block:**

> "The 30-Day Effective Yield … **is net of fees and reflects fee waivers from Morgan Stanley
> Investment Management. Fee waivers may be reduced or discontinued. Absent fee waivers, yields
> would have been lower.** MCRYX **has a floating NAV, is not a money market fund, and carries
> principal risk.** Yields fluctuate, can decline, and are not guaranteed."

**Treasury is not a deposit:**

> "Treasury accounts are **not FDIC insured, are not bank deposits**, and are not guaranteed by
> Choice Financial Group or Column N.A., and **may lose value**." Brokerage and clearing by **Apex
> Clearing Corporation**, SEC-registered broker dealer, FINRA and SIPC, licensed in 53 states and
> territories.

**Relationship managers, a threshold not previously recorded:**

> "**Relationship Managers are available to Pro subscribers and for business accounts with $10M+
> balance.**"

This is **$10M, not $25M**. `docs/outreach_rules.md` built its lane split partly on the assumption
that a named human appears at $25M. See correction #23. It also establishes that Mercury sells a
paid **Pro** subscription, not previously recorded.

**The "1 in 3 startups" footnote, which partially quantifies the unresolvable problem in section
3b:**

> "Calculation based on **US-based companies that received an angel, pre-seed, seed, or Series A
> investment reported on Crunchbase in the most recent year.**"

The claim is scoped to **early-stage US rounds in the last year**, which is very close to the
population a Form D pull produces. So roughly **one in three names on our list may already be
Mercury customers**, and the "1 in 3" is not a whole-market figure.

**Venture debt geography (out of scope, recorded for completeness):**

> "At this time, we are **unable to offer working capital or venture debt loans to businesses
> operating in California**."

**Cards:** IO Card issued by **Patriot Bank, N.A.**, Mastercard licence. Cashback "automatically
credited to your linked checking account **when your monthly repayment is processed**", proportional
on early payment, forfeited on account closure, programme may be modified or terminated.

**Real-Time Payments:** "available only to Mercury customers whose accounts are provided through
**Column, N.A.**" Not universal.

**Personal savings APY:** "accurate as of 06/15/2026. **This is a variable rate account.**"
