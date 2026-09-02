# Primary-source evidence: `demo.mercury.com`, captured 2026-08-29

**Why this capture exists.** Every copy angle in this build was a feature list read off the
homepage: zero minimums, ten-minute application, $0 wires, 1.5% cashback, day-one card, $5M FDIC.
The user pointed out that Mercury ships a **live product demo with two role views**, and that the
role split is a benefit the feature list cannot express. It is captured here so copy can be written
against the product rather than against the marketing page.

**How it was captured.** In-browser, no authentication, no account created, nothing submitted. The
demo is public and unauthenticated: the top bar shows "Open account", i.e. the viewer is signed out.

| | |
|---|---|
| **URL** | <https://demo.mercury.com> |
| **Fetched** | 2026-08-29 |
| **Method** | Browser pane: `navigate`, `get_page_text`, `computer{screenshot}`. Toggled the role control in the top bar |
| **Auth** | none. Signed out throughout |
| **Actions taken** | Role toggle only. No form filled, nothing submitted, no account opened |

Every quoted string below is verbatim from the rendered page.

---

## A. The role control, which is the point of this file

The top bar carries a role switcher: **"Viewing as Admin"**, opening to **"View as Employee"**. The
same demo tenant, the same data, two role-scoped renderings.

### The employee-view panel, verbatim

> **See your employees' view of Mercury**
>
> **"The Employee role grants access to cards and reimbursements while hiding sensitive info
> related to your account."**
>
> - See how employees view transactions
> - See how employees work on tasks
> - Try submitting a reimbursement

**That sentence is the strongest single line for this campaign's copy** and it is Mercury's own. It
is a permissions claim, not a feature claim, and permissions are what a company that just hired
twelve people actually has a problem with.

---

## B. The two navigations, side by side

Captured from the left rail in each role.

| Admin | Employee |
|---|---|
| Home | Home |
| Tasks **(10)** | Tasks **(1)** |
| Command *(New)* | Command *(New)* |
| **Accounts** | — |
| Transactions | Transactions |
| Cards | Cards |
| **Team Spend** | — |
| **Payments** | — |
| **Invoicing** | — |
| **Accounting** | — |
| — | **Budgets** |
| — | **Reimbursements** |

Admin also carries a **Bookmarks** section: `Ops / Payroll $2,023,267.12`, `Credit Card`,
`Bill Pay`, `Insights`. The employee view has no bookmarks rail.

**Six sections disappear for an employee; two appear.** The demonstration of "hiding sensitive info"
is structural, not a disclaimer.

---

## C. What each role sees on Home

### Admin

> **Welcome, Jane**
> Send · Transfer · Deposit · Request · Upload bill
>
> **Mercury balance** **$5,216,471.18** · Last 30 days · ↗ $1.8M ↘ −$465K
>
> **Accounts:** Credit Card `$12,505.87` · **Treasury `$200,000.00`** · Ops / Payroll
> `$2,023,267.12` · AP `$226,767.82` · AR `$0.00` · +2 View all accounts
>
> **Credit Card** `$12,505.87` · `$21,249 available` · Autopay Sep 3
> **Bill Pay** Outstanding 11 · Overdue 1 · Inbox 3 items · $10K
> **Invoicing** Overdue 4 · $950.00 · Paid 12 · $6K · Open 12 items · $12.3K
>
> **Money movement, Aug 2026**
> Money in **$1,769,353.65**. Top sources: **Venture Debt Loan $1,000,000.00**, GenPro
> $415,133.44, Google $69,774.47, Milgram Brokerage $60,499.95
> Money out **−$474,484.98**. Top spend: Jordi O'Donnell −$90,797.16, **Gusto (Payroll)**
> −$90,122.53, Google −$71,055.95

The admin transactions table attributes card spend to **named people**: `Alice C. ••1234`,
`Mary M. ••0332`, `Jane B. ••6112`, `Jessica A. ••9914`.

### Employee

> **Welcome, Jane**
>
> **Upload receipts from your inbox** — "Email receipts from card transactions to
> `receipts@mercury.com` and we'll match them to the right transaction."
>
> **1 task needs your attention** — "Review pending emails that can auto-forward to
> receipts@mercury.com"
>
> **$92.59 available to spend on budgets**
> Team Lunch `$21.64 available` · Hardware `$4.84 available` · Software Subscriptions
> `$66.11 available`
>
> Transactions, scoped to their own cards, with a **Budget** column

**The $5.2M balance does not appear anywhere in the employee view.** Neither do Accounts, Payments,
Invoicing, Accounting or Team Spend. The employee sees a spend allowance and their own receipts.

---

## D. The "Try out Mercury for yourself" panel (admin view)

Persona tabs, in page order: **Startup · Ecommerce · Agency · More**

Actions offered:

> - Send money to contractors
> - **Invite your team members**
> - **Create cards for your team**
> - Request vendor payment details
> - **Issue SAFE to investors**
> - Understand your data — *Try Command*

Two of these matter to this build:

1. **"Issue SAFE to investors."** `SAFE` is a Form D `securityType` value, so a row whose security
   type is a SAFE has a demo action written for its exact situation. This is a copy input, not a
   scoring input.
2. **The persona tabs are the ICP**, and they match the homepage footer segments already mapped in
   `docs/mercury_offer.md` section 5.

---

## E. Recorded, and deliberately not used

**"Venture Debt Loan $1,000,000.00" is the single largest money-in source in the demo.** Mercury
puts its own lending product at the top of the cash-in list on the page it uses to sell the account.

This is noted and **not acted on.** Venture Debt is out of scope by standing rule
(`CLAUDE.md`, `docs/mercury_offer.md` section 6c): not built, not routed to, not named as a lane,
not mentioned in the Loom as something this system does. It is recorded here only so that a later
reader does not re-derive it.

---

## F. What this capture changes

| Before | After |
|---|---|
| Copy listed account features: zero minimums, $0 wires, 1.5% cashback, $5M FDIC | Copy also carries the **role split**, in Mercury's own words, which is a benefit no feature list states |
| The CTA was "open an account", a high-commitment ask to a stranger | **"Launch demo"** is a real Mercury CTA to a real public URL, and it costs the reader nothing |
| Admin and employee were undifferentiated | Two named audiences with different problems: the founder wants control and visibility, the hire wants a card that works and receipts that file themselves |

**A caution that travels with all of it.** This is a **demo tenant with synthetic data**. Every
number above (`$5,216,471.18`, `$200,000.00` in Treasury, `$92.59` of budget) is Mercury's
illustration, not a customer's balance and not a benchmark. **No figure from this file is ever
quoted in outbound copy.** What is usable is the *structure*: which roles exist, what each can see,
and the one verbatim sentence in section A.
