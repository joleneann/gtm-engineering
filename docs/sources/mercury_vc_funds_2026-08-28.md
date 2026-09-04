# Primary-source evidence: mercury.com/vc-funds, captured 2026-08-28

Fetched to settle whether Mercury's Treasury eligibility rules exclude venture funds. They do not,
and this page is the disproof. See `docs/verification_log.md` #25.

Re-capture command:

```bash
curl -s -L -A "Mozilla/5.0" https://mercury.com/vc-funds
```

Page title: **"Venture Capital Fund Banking | Mercury"**. Sibling URLs probed and returned 404:
`/solutions/vc-funds`, `/venture-capital`.

---

## Hero

> **First-class banking for VC funds**
> **Join 2,500+ VC funds that bank with Mercury** to manage investments in their portfolio companies.
> [Enter your email] Open account | Contact sales

> Mercury is a fintech company, not an FDIC-insured bank. Banking services provided through Choice
> Financial Group and Column N.A., Members FDIC.

## The VC Funds value proposition, in full

> **Store your funds with complete confidence** — Join the thousands of venture capital firms that
> trust Mercury to manage risk and protect their capital with **up to $5M in FDIC insurance**
> through our partner banks and their sweep networks.
>
> **Unlock international capabilities** — Easily send wire payments from your entities to your
> portfolio companies.
>
> **Move funds the moment they're needed** — Get capital to portfolio companies in seconds with
> **real-time payments**, or send wires and ACH when you need to.
>
> **One-on-one expert guidance** — "Your needs come first, and high-touch, white-glove service is
> part of the Mercury package for VC funds. Bank with confidence knowing your **dedicated
> relationship manager is always one message away**."
>
> **Manage all your accounts from one place** — "Create separate accounts for **your fund, your
> SPVs, and your management company**, and toggle between them with ease."
>
> **File 1099s right from Mercury** — Collect W-9s, prefill with AI extraction, file Federal and
> State 1099-NEC and MISC for the 2025 tax season.
>
> **Benefits that reach your whole portfolio** — **Venture Debt**: diligence done entirely online,
> with VC-friendly terms. **IO Mastercard**: 1.5% cashback.

**Treasury does not appear anywhere in the VC Funds value proposition.** It sits in the site-wide
product nav on this page as "Treasury by Mercury Advisory", as it does on every page, but the
segment pitch is FDIC coverage, payments speed, SPV account structure, 1099 filing, Venture Debt and
the card. This is a fact about what Mercury sells funds, not a rule about what funds may buy.

## Named customers, usable as suppression-list seeds

| Person | Role | Firm |
|---|---|---|
| Zann Ali | Partner | **2048 Ventures** |
| Wiz Abdullah | Co-founder & Partner | **Spacecadet Ventures** |
| James Beshara | Angel investor | (individual) |

## FAQ, verbatim extracts

> **What do I need to apply for an account?** … "Customers must be **formed and registered in the
> United States or a U.S. territory**, have some type of **existing or planned operations in the
> U.S.**, and have a U.S. or international address for their principal place of business. This can
> be a residential address, but **may not be a registered agent, P.O. box, or UPS box address**."

That last clause is a **banking** onboarding rule, distinct from the Treasury eligibility list in
section D of `mercury_treasury_2026-08-28.md`, and it matters under a "open a Mercury account"
campaign: a Form D issuer address that is a registered agent (common in Delaware) fails it.

> **Are my deposits FDIC-insured?** "Mercury checking and savings deposits are FDIC-insured up to
> $5M through our partner banks and their use of sweep networks."
>
> **Where are my funds kept?** "Through each of our partner banks, Mercury customers get access to a
> sweep network of trusted banks. This sweep network provides up to $5M in FDIC insurance by
> **automatically spreading your deposits across up to 20 different banks**, without requiring you
> to open and manage separate bank accounts."

---

## What this settles

1. **Mercury banks venture funds, at scale, and says so as a headline.** "2,500+" is quoted.
2. **Mercury banks the fund, the SPVs and the management company as separate account holders**, so
   the three entity types are distinguished by the seller itself. Only the management company is
   plainly an "investment adviser" under the Treasury exclusion list.
3. **Every VC fund customer gets a relationship manager**, independent of the $10M balance rule and
   the Pro subscription recorded in #23. Three RM paths now, not one.
4. **The Form D `Pooled Investment Fund` gate cannot be justified by the eligibility list.** Its
   justification is Form D's own Item 13 instruction, that the sold amount includes "cash to be paid
   in the future under mandatory capital commitments", so the field can report money not received and
   cannot share a scoring scale with a figure read as cash on hand. Corrected 2026-09-04: this
   paragraph is analysis, not capture, and previously asserted a drawdown period the form does not
   state. The captured text in this file is untouched.
