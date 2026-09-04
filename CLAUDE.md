# Operating contract: GTM Engineering build

`docs/source_of_truth.md` is the only record of what this system is and does. Read it before planning
anything. This file holds process rules only; it contains no product or pipeline facts, because that
is how the last one went stale.

---

## RULE ZERO: no drift

**A decision is not made until it is written.** The moment a decision is settled in conversation, and
before any code is written, any schema applied, or the turn ends:

1. `docs/source_of_truth.md` is edited so it **reads correctly**. The superseded sentence is deleted.
   Never annotated, never left standing next to its own correction.
2. This file is edited if the decision changes a rule.
3. The changelog at the top of `docs/source_of_truth.md` gains a dated row: what changed, and the
   `withdrawn_phrase` that must never reappear.

A turn that ends with a decision made and the documents not updated is a defect, and it is fixed
before anything else proceeds.

Enforced by `scripts/00_doc_check.py`, which **reads every file** under `docs/` and this file in full
and fails if a withdrawn phrase reappears. It reads rather than greps a filtered subset, because the
previous version of this check certified a file as clean while the withdrawn rule was sitting in it.
Run it at the end of every step.

## The plan

`plans/build_plan.md` holds the step order: which step is next, what each reads and writes, and how
each is verified. Read it at the start of a session before asking what to do; a session once spent its
opening turns hunting for it because this rule did not exist.

It is the execution order and nothing more. **The source of truth wins on every fact**, and where the
two disagree the plan is what is wrong. `plans/` is gitignored, and the plan never moves under `docs/`:
it names decisions by their superseded wording, so the no-drift check correctly fails it as a live
document. When a step finishes or a rule changes, the plan is corrected in the same turn as the source
of truth.

## Scope

- Execute only the step named this session. Do not start, scaffold, or prepare future steps. Do not
  refactor earlier steps unless asked.
- Two things are never designed alone: the scoring model and the CRM data model. Bring candidates and
  reasoning; never present a finished model. The scoring model is settled and lives in the source of
  truth. The CRM model is not.

## Method sheet before every step

Nothing executes until the user signs off a sheet stating: what it reads, what it writes, the exact
method or formula or payload, its assumptions, its known failure modes, and the verification that
proves it worked.

## Schema is law

- `db/schema.sql` is the single source of truth for the database. Never create, rename or drop a table
  or column that is not in it.
- A step needing a schema change stops, explains why, proposes the exact DDL, and waits. Approved
  changes go into `db/schema.sql` first, then get applied.
- Schema is applied through the Supabase SQL editor from a versioned file with a diff and a revert.
  Never by a script. Never through MCP.
- Supabase MCP is read-only and for inspection. All writes go through Python using
  `SUPABASE_SERVICE_ROLE_KEY`.

## Money

Budget is **$0**. Nothing here requires payment.

- Before any call that could bill, print the exact payload and the projected cost, stop, and ask.
  Never batch-confirm.
- Micro-test at minimal volume before any scaled run, and observe the real per-unit charge rather than
  trusting a published rate. A headline "from $X" is the floor tier, not the free one.
- **No scraping.** SEC EDGAR is a public REST API.
- Clay free tier is the binding constraint: 100 data credits and 500 actions a month, 200 rows per
  table, no HTTP API column, no scheduled runs. Every paid Clay column carries a run condition, and
  the condition sits on the **first** paid column, not somewhere downstream.
- Log actual spend and actual credit usage after a run, never before. Do not estimate credits.

## Reliability

- All writes are idempotent upserts. Every script safe to re-run.
- **A known rate limit is paced around, never retried into.** The SEC puller throttles below 10
  req/sec; the sender knows its budget before the run and never queues more than it can deliver. A 429
  anywhere means the pacing is wrong.
- **No dead-letter table and no run log.** A script asserts a complete pull and fails loudly if it is
  short. If something fails, find out why, fix it, and re-run until the assertion passes. Because
  every write is an idempotent upsert, re-running is free and safe, and nothing is allowed to end in a
  partial state.
- **A reason code must be reachable at real volume**, and its measured rate is recorded in the
  `reason_codes` table. A code for a condition that cannot occur is padding.
- A missing value is not a disqualification. Nulls route out with an explicit code and are counted in
  the funnel, never silently rejected.
- **No human review queue.** Where a judgement was previously deferred to a person, the system decides
  and the decision is counted. Ambiguity is dropped rather than guessed, because emailing the wrong
  company is worse than sending nothing.
- Partial writes must be resumable: write back an id the moment the record exists.

## Secrets and data

- Credentials come from `.env` only. Never hardcode, echo, or commit a secret.
- Real contact data lives only in Supabase and `exports/`, both gitignored.
- Anything committed or printed as an example uses redacted or synthetic values.

## Compliance

- Nothing is ever sent to a real company. The only sendable rows are the seeded test rows using
  `TEST_EMAIL` / `TEST_PHONE`.
- That rule is enforced by a hard failure inside the workflow, not by convention.
- Real accounts get a prepared task and a drafted message. A human sends it or nobody does.

## Claims and numbers

- Never state a count, ranking, total or projection until a real script has produced it. Show the run.
- Never use a documented claim as a design rationale without checking it against the live data or the
  actual file first.
- When the spec and reality conflict, stop and say so. The source of truth gets amended first; code
  follows it, never the reverse.
- Every figure is labelled **quoted** or **derived**, and a derived figure shows its working. A
  direction, ordering or trend a page does not state is never written as though it did. Page
  summarisers infer; only the raw page counts as quoted.
- `docs/sources/` is the evidence archive: verbatim captures with their fetch date and the command
  that produced them. Read it instead of re-fetching. A refresh replaces the file with a new dated one
  rather than editing the old.

## Process

- Plan first: state what will be read, what will be written, which tables change, expected row counts,
  and cost. Wait for an explicit go.
- One script per step in `scripts/`, numbered to match the plan. No monoliths.
- End every step with its verification block: row counts, spot-check sample, caps respected, cost
  logged. Print it. Never self-declare success without it.
- If something fails, show the actual error before attempting a fix. Do not silently switch
  approaches, libraries or data sources.

## Writing

- No em dashes. Use colons, semicolons, commas, or restructure.
- No AI or assistant attribution anywhere in git history: no `Co-Authored-By`, no "Generated with"
  line, no mention of Claude or Anthropic in a commit message or PR description.
