# CashFlowIQ — Seed Data Spec

Synthetic transaction data is the **test fixture** for the scoring engine. It's designed, not random: each archetype exercises a distinct scoring path, so the four signals and the ExplanationAgent can be validated against known-good cases.

## Archetypes (5 profiles, not N random clients)

Each profile is chosen to stress a specific part of the scoring engine:

| Profile | Story | Exercises |
|---|---|---|
| **Strong approve** | Stable income, low expenses, positive balance trend | High-score path; score 80+ |
| **Clear decline** | Volatile income, overdraft clusters | Adverse-action / ExplanationAgent path; score <40 |
| **Marginal** | Mixed signals, thin margins + a shock | Boundary / tier logic |
| **Thin file** | Few transactions | CoV with small n (statistical edge case) |
| **Gig worker** | Irregular DoorDash/Uber deposits | Prism's core use case; income-detection under noise |

**Built so far:** Bob (marginal — small business, thin margins + June pipe-repair shock) and Patricia (strong approve — stable salaried consumer). The other three are future parameter sets.

## Window

- **~90 days, parameterized** (not hardcoded). Current build: 2026-04-01 .. 2026-07-01.
- **Justification:** the minimum window where all four signals are meaningful — ~6 biweekly paychecks for income CoV, ~3 occurrences to confirm recurrence, ~90 balance points for trend regression. Matches the shortest realistic aggregator pull.
- **Vocabulary (don't conflate in interviews):** Prism's *12 months* is the **prediction horizon** (default within the next 12 months), NOT the input lookback window. Input window ≠ performance window.

## Realism rules

- Payroll: same amount, same cadence, same descriptor.
- Rent: fixed amount, mostly on the 1st, with occasional date drift (tests payee-vs-amount recurrence, not exact-date matching).
- Subscriptions / credit-card payments: fixed amounts, end of month.
- Utilities: same payee, small seasonal variation.
- Groceries / dining: irregular.
- Overdraft/NSF fees: ~$35, clustering late in pay periods (decline archetype).
- **One-offs are `other`, never `recurring_expense`** — mislabeling a shock as recurring inflates the recurring-expense ratio.

## Build approach

- **Parameterized generator**, not hardcoded rows — archetypes become parameter changes. (Currently a readable helper + per-profile loops; refactor to a pure-parameter engine when the 3rd archetype lands — rule of three.)
- **Reproducible:** current profiles are explicit (no RNG). When random jitter is introduced (gig worker), seed it (`random.seed(42)`) — a deterministic-scoring pitch demands a deterministic demo.
- **Descriptors** use realistic-ish notes (`#rent`, `#payroll`, ...); upgrade path is full bank-string format (`"ACH DEPOSIT ACME CORP PAYROLL 0715"`), which is literally what Prism's categorization product cleans up.

## Day-3 items (need the scoring engine first)

- One pytest per archetype asserting the score lands in its expected band (approve >75, decline <40, ...) → turns the seed into a regression suite.
- 30-day degradation case: run a profile with only 30 days and decide explicitly what the API does (score + confidence flag? reject with 422?). You will be asked this.
- Add the remaining 3 archetypes (decline, thin file, gig worker) as parameter sets.

## Decisions logged

- Chose 5 archetypal profiles over N random clients — each exercises a distinct scoring path.
- Chose a 90-day parameterized window — the statistical floor for all four scoring signals.

## Scoring calibration — accept honest scores, don't overfit
Archetype composites: Patricia ~95 (strong approve), Bob ~77 (healthy, thin margins),
John ~35 (lean decline). We initially expected Bob=marginal and John=clear-decline, but the
data doesn't support those labels: Bob has positive cash flow, zero overdrafts, stable income,
and a rising balance — his only weakness is a high expense ratio; John's MONTHLY income is
stable (per the monthly-CoV choice), which legitimately floors his score above rock-bottom.
Rather than reverse-engineer thresholds to force predetermined labels onto three synthetic
customers (overfitting — indefensible in review), we set thresholds from domain reasoning and
accept the resulting scores. Labels updated to match the data. Thresholds to be recalibrated
against real repayment performance data.