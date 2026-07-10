Lines 32-34 in models.py - "I constrained direction at the schema level with an enum instead of validating in application code, so bad values can't exist in the database." 

"I used create_all for the prototype and documented Alembic as the migration path in the README."

That id 1 is "missing" because of my earlier shell experiment — the Test business got sequence value 1 when I flushed it, Postgres sequences don't roll back. So gaps in an auto-increment id are normal and expected — not a bug

# Decisions Log — CashFlowIQ

Running log of "chose X over Y because Z." Reconcile with any entries you've kept locally.

## Architecture
- **Deterministic layer decides; LLM only narrates.** The scoring is transparent, testable math; the ExplanationAgent puts an already-computed score into words and never touches the number. Reason: ECOA/Reg B adverse-action notices require consistent, auditable reasons — regulatory, not stylistic.
- **Three-layer split** (routers → services → models), `config.py` fail-fast env, session-per-request. Reason: isolates HTTP, domain logic, and persistence so each is testable in isolation.
- **`models.py` separate from `schemas.py`** (DB shape vs API contract). Reason: the wire format and the storage format change for different reasons.

## Scoring
- **0–100 transparent composite, NOT CashScore's 0–999.** Reason: 0–999 is a *validated statistical default model*; copying the range without the model is cargo-culting. Naming the difference shows understanding of Prism's product.
- **Four signals:** income stability (CoV), recurring expense ratio, overdraft/NSF frequency, balance trend (linear regression).

## Data model
- **Top entity is `Customer`, not `Business`.** Reason: ~70% of Prism's volume is lenders pulling *private-borrower* deposit data; the primary use case is consumer, not SMB.
- **Money is `Numeric(12,2)`, never `float`.** Reason: binary floats can't represent decimal cents exactly; error accumulates until the ledger won't tie out.
- **FK on the many side** (BankAccount.customer_id, Transaction.account_id). Reason: a single FK column expresses "one parent per row."
- **`amount` positive; `direction` enum carries sign; balance derived (deposits − withdrawals), not stored.** Reason: a stored balance drifts out of sync with its transactions.
- **`direction` and `category` as DB-level enums.** Reason: constrain valid values at the schema level, not in application code — bad values can't exist.
- **One-time expenses are `Category.other`, not `recurring_expense`.** Reason: mislabeling a shock as recurring inflates the recurring-expense ratio.
- **`description` is NOT NULL.** Reason: a real bank transaction always has a descriptor.
- **Composite index on `(account_id, date)`.** Reason: serves the core metrics query `WHERE account_id = ? ORDER BY date`.

## Infrastructure
- **Postgres 18 in Docker**, host port **5433** (`"5433:5432"`). Reason: avoids collision with a local Postgres 18 install squatting on 5432.
- **Volume mount `/var/lib/postgresql`** (not `/data`). Reason: Postgres 18 changed the data-dir layout; the old mount crash-loops.
- **`create_all` now; Alembic migrations deferred (documented).** Reason: prototype speed. Known cost: schema changes require drop/recreate — which is exactly the pain Alembic solves.
- **Unique host port per project** (CashFlowIQ 5433). Reason: two dockerized DBs can't share a host port; container port stays 5432.
- **`requirements.txt` via `pip freeze`.** Reason: the venv is disposable; rebuild with one command.

## Tooling / process
- **Sync-first (`psycopg2`), async deferred.** Reason: fewer moving parts; convert only if proven necessary.
- **Synthetic seed data, categorization not faked.** Reason: assign categories directly in the fixture; document the aggregator (Plaid/Prism) as the production dependency (parallels ParcelIQ's no-fake-geospatial).

## Income stability signal — monthly CoV, complete months only
- Chose monthly-total income CoV over per-deposit CoV: measures predictability of earning
  POWER, not payroll timing; avoids penalizing irregular pay cycles (gig workers).
- Consequence (defensible in interview): all 3 seed archetypes have stable monthly income
  (CoV ~0–0.03), so this signal does NOT separate them. John's decline is driven by the
  OTHER signals (expense ratio, overdrafts, balance trend), not income instability.
  Correctness proven via unit tests; a future "feast-or-famine" archetype would demonstrate it.
- CoV → sub-score bands: <0.10→100, 0.10–0.25→75, 0.25–0.50→45, >0.50→15.

## Scoring window — 3 complete months (2026-04-01 .. 2026-06-30)
- Excluded the partial boundary month (July): Patricia's 7/1 paycheck, John's 7/8 card
  payment + 7/9 overdraft fee, Bob's 7/1 items. A partial month distorts monthly-aggregated
  signals — e.g. Patricia's lone 7/1 paycheck would fake a low month and inflate her income
  CoV, wrongly penalizing the strongest customer. Score complete months only, uniformly
  across all four signals.

## Overdraft Count
- a count is window-specific — "4 fees" means something different over 3 months vs 12. Fine for a fixed-window demo; we'd revisit rate-based if the window ever becomes variable.
- Overdrafts are direct liquidity-failure events, so the score declines sharply after the first occurrence rather than linearly rewarding low counts.
- Overdraft bands were chosen from domain reasoning, not to force archetype outcomes. Thresholds and scores should be recalibrated against observed repayment performance.

## Net Cash Flow Ratio
- Balance signal uses a net-cash-flow-to-income proxy rather than a daily-balance regression. The available dataset contains transactions but no opening balance or balance snapshots, so constructing a running balance would require an invented starting value. The proxy is scale-independent and explainable. A production version would use actual balance snapshots and regress daily balance against time.
- Net cash-flow proxy includes all observed spending withdrawals except transfers. Recurring expenses, fees, and other withdrawals reduce net cash flow because they consume funds during the scoring window. Transfers are excluded because they may represent movement between customer-owned accounts rather than economic spending. This keeps the recurring-expense signal focused on committed obligations while allowing one-time shocks to affect the broader cash-flow signal.