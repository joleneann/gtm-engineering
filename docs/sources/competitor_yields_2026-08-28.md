# Primary-source evidence: competitor yields, captured 2026-08-28

Fetched to settle open items A2 ("Arc quotes a higher yield" — asserted, never checked) and
A3 ("their current bank pays ~$0" — asserted, never checked). Both were wrong in the direction
that flatters Mercury.

Re-capture commands:

```bash
curl -s -L -A "Mozilla/5.0" https://www.joinarc.com/treasury-investment-options
curl -s -L -A "Mozilla/5.0" https://www.brex.com/product/business-account
```

---

## A. Arc (`joinarc.com`), verbatim

Headline: **"Earn up to 4.65%² yield"**.

Footnote 2, verbatim:

> "Reflects the highest net yield available as of the most recent business day in Arc Treasury, by
> Arc Advisory LLC, **for Arc Premium subscribers** unless otherwise noted. Certain investment
> options, including potentially the highest-yielding, **may have investment minimums**."

The investment-options page ships a machine-readable table. Reproduced exactly:

| Option | Liquidity | Gross | Net (Premium) | Net (Essentials) |
|---|---|---|---|---|
| Insured Deposit Programs (sweep) | 1 business day, $2.5M FDIC-eligible | 0.45% | 0.35% | **0%** |
| Vanguard Federal MMF (VMFXX) | 1 business day | 3.62% | 3.52% | 3.12% |
| Dreyfus Institutional Preferred Govt MMF (DSVXX) | 1 business day | 3.62% | 3.52% | 3.12% |
| Morgan Stanley Inst. Fund Trust Class A (MUAIX) | 1 business day | 3.69% | 3.59% | 3.19% |
| Morgan Stanley Inst. Fund Trust Class IR | 1 business day, **$10M minimum** | 3.84% | 3.74% | 3.34% |
| **Vanguard Short-Term Investment-Grade (VFSTX)** | 1 business day | 4.75% | **4.65%** | 4.25% |
| 1 / 3 / 6 / 12 month T-Bill | held to maturity | 3.70–4.00% | 3.60–3.90% | 3.20–3.50% |

**The 4.65% headline is a short-term corporate bond fund, not a money market fund**, and it is the
Premium (paid-tier) net figure. Arc's fee is the gap between gross and net: **10 bps on Premium,
50 bps on Essentials**, flat, not tiered by balance.

## B. Brex (`brex.com/product/business-account`), verbatim

> "Earn up to **3.71%†** in a treasury account with **no minimum deposit**."
> "Up to **$6M in FDIC coverage**"

Footnote †, verbatim:

> "Total treasury return **includes yield and additional return** and is subject to the total
> balance in Checking, Treasury, and Vault. Yield is the annual percentage rate based on the
> current 7-day average yield for the **BNY Dreyfus Government Cash Management (DGVXX)**, and is
> effective as of 08/27/26. **Additional return** is effective as of 08/27/26 and **paid by Brex
> Treasury LLC**…"

Brex's own FAQ block gives a second, lower number for the same product:

> "You can earn up to **3.64%** yield with same-hour liquidity and no minimum deposit."

And a direct swipe at Mercury's gate, unnamed:

> "Funds invested in Treasury can earn yield with **no minimum deposit, unlike some providers that
> require minimum balances to access yield**."

**3.71% is not a fund yield.** It is a fund yield plus a promotional subsidy paid by Brex itself,
and it is tiered on total balance across three products. The underlying fund yield is DGVXX's
7-day average.

## C. Where "Dreyfus" came from

Correction #5 in `docs/verification_log.md` recorded that a comparison blog wrongly attributed a
"Dreyfus" fund to Mercury. This capture identifies the source of the error: **Dreyfus is Brex's
fund (DGVXX)**, and Arc offers a second Dreyfus fund (DSVXX). The blog took a competitor's fund and
printed it under Mercury's name.

---

## D. Like-for-like comparison at the tier our leads actually land in

Median Form D round in the measured day was **$1,633,750**, which puts almost every lead in
Mercury's **lowest** band. Same-risk products compared:

| Government money market, high liquidity | Net yield |
|---|---|
| Brex DGVXX, same-hour, no minimum | up to **3.71%** (incl. subsidy) / 3.64% stated |
| Arc VMFXX or DSVXX, 1 business day, Premium tier | **3.52%** |
| **Mercury MRGXX, same-day, $250K–$2M** | **3.12%** |
| Arc, Essentials tier | 3.12% |

| Ultra-short / short bond, 1–2 day liquidity | Net yield |
|---|---|
| **Arc VFSTX, Premium** | **4.65%** |
| Arc VFSTX, Essentials | 4.25% |
| **Mercury MCRYX, $250K–$2M** | **3.44%** |
| Mercury MCRYX, $20–50M (the headline) | 3.89% |

**Mercury is last or joint-last on yield at the balance our leads actually have, in both risk
classes, and it is the only one of the three with a minimum balance to qualify at all.**

Mercury only reaches parity at $20M+, which is a small minority of the list.

**Consequence: yield cannot be the lead in the copy.** Section 6 of `docs/mercury_offer.md` had
already concluded that from Mercury's own page ("the differentiator is not the biggest number");
this capture proves it with the competitors' own numbers rather than inferring it.
