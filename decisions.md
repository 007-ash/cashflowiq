# Decision Log - CashFlowIQ

CashFlowIQ started with a simple question: can current cash-flow behavior add useful context for people who have little or no borrowing history?

I wanted the answer to be understandable, not hidden inside a black box. This file records the choices that keep the project transparent: what I built, what I rejected, and what would need to change before the system could be used with real borrowers.

> CashFlowIQ is a portfolio project. It is not a validated credit model or a production lending system.

## 1. Core Architecture

### The scoring code decides; the LLM only explains

The deterministic layer calculates:

- four signal scores
- the weighted composite score
- the final risk tier

The ExplanationAgent receives qualitative signal labels derived from that completed report and returns structured prose.

It does not receive raw transactions, exact signal values, the overall score, or the risk tier.

Reason: the most important result in the system should be reproducible. The same transaction data should produce the same score every time, regardless of whether the model provider is available.

### Responsibilities are separated by module

- `routers/` handles HTTP requests, database coordination, and HTTP errors.
- `metrics.py` contains deterministic scoring logic.
- `models.py` defines SQLAlchemy database models.
- `schemas.py` defines API request and response shapes.
- `explanation_agent.py` contains the optional explanation layer.

Reason: scoring, persistence, HTTP behavior, and model-provider behavior change for different reasons. Keeping them separate makes each part easier to test and replace.

### Explanation failure should not erase the report

When explanation generation fails, the endpoint still returns the deterministic score, tier, and signal results:

```json
{
  "explanation": null,
  "explanation_status": "unavailable"
}
```

Reason: the score is the product. The explanation is an enhancement.

## 2. Observation Window

The demo uses three complete calendar months:

```text
2026-04-01 inclusive
2026-07-01 exclusive
```

July is excluded because it is incomplete in the seed data.

Reason: partial months distort monthly comparisons. A single paycheck or expense near a boundary can make a stable account look unstable.

The same window is used for all four signals so the report is internally consistent.

## 3. Scoring Model

### Composite scale

CashFlowIQ uses a transparent 0-100 weighted score.

I chose this range because it is easy to read and explain. It is not meant to copy or imitate a commercial score range.

The project demonstrates an auditable weighted model, not a statistically validated probability-of-default model.

### Current signal weights

| Signal | Weight |
|---|---:|
| Income stability | 15% |
| Recurring expense ratio | 25% |
| Overdraft count | 30% |
| Net cash flow ratio | 30% |

The final score is rounded once after all weighted contributions are added.

Overdraft count and net cash flow receive the largest weights because they capture direct signs of liquidity pressure. Recurring expenses receive a substantial weight because fixed obligations reduce flexibility. Income stability is useful context, but stable income alone does not protect a customer who consistently spends beyond available cash.

These weights are expert judgment for the prototype. They have not been calibrated against repayment outcomes.

### Risk tiers

```text
80-100: low
60-79:  moderate
40-59:  elevated
0-39:   high
```

Each lower boundary is inclusive.

## 4. Signal Decisions

### Income stability

Monthly qualifying income is grouped by calendar month. Stability is measured with the coefficient of variation:

```text
population standard deviation / mean monthly income
```

Reason: monthly totals measure earning consistency without penalizing someone only because they are paid weekly, biweekly, or on an irregular schedule.

At least two complete months are required.

Current bands:

| Coefficient of variation | Score |
|---:|---:|
| `< 0.10` | 100 |
| `0.10 to < 0.20` | 80 |
| `0.20 to < 0.35` | 55 |
| `0.35 to < 0.55` | 30 |
| `>= 0.55` | 10 |

The seeded customers all have relatively stable monthly income. That is intentional: income stability should not be forced to separate every customer. Overspending and liquidity pressure should appear in the signals designed to measure them.

### Recurring expense ratio

Formula:

```text
total recurring expenses / total qualifying income
```

Reason: this measures how much of a customer's income is already committed to recurring obligations.

Transfers and one-time expenses are not counted as recurring obligations.

Current bands:

| Ratio | Score |
|---:|---:|
| `< 0.40` | 100 |
| `0.40 to < 0.60` | 80 |
| `0.60 to < 0.75` | 55 |
| `0.75 to < 0.90` | 30 |
| `>= 0.90` | 10 |

A zero qualifying-income denominator is treated as invalid scoring data. The code fails instead of creating a misleading ratio.

### Overdraft count

The prototype counts transactions categorized as fees during the fixed three-month window.

The seed data assumes `Category.fee` represents overdraft or NSF fees.

Reason: a count is easy to explain and is reasonable while the observation window is fixed. A future variable window would require reconsidering a rate-based measure.

Current bands:

| Count | Score |
|---:|---:|
| `0` | 100 |
| `1` | 70 |
| `2` | 45 |
| `3` | 25 |
| `4+` | 10 |

The bands were chosen from domain reasoning, not adjusted to force a preferred result for a specific seed customer.

### Net cash flow ratio

I originally considered a running-balance trend. I rejected it because the dataset has transactions but no opening balance or balance snapshots. Inventing a starting balance would make the trend look precise without being trustworthy.

Current formula:

```text
income - recurring expenses - fees - other withdrawals
-------------------------------------------------------
                  qualifying income
```

Transfers are excluded because they may be movement between a customer's own accounts.

Miscellaneous deposits are excluded because refunds, gifts, and similar inflows are not treated as repeatable income.

Other withdrawals remain included because they reduce available cash during the observation window.

Current bands:

| Ratio | Score |
|---:|---:|
| `< -0.30` | 10 |
| `-0.30 to < -0.10` | 30 |
| `-0.10 to < 0.10` | 55 |
| `0.10 to < 0.40` | 80 |
| `>= 0.40` | 100 |

A production version with reliable daily balance snapshots could evaluate balance behavior directly.

## 5. Data Model

### Customer is the top-level entity

The current relationship is:

```text
Customer -> BankAccount -> Transaction
```

Reason: the project is centered on an individual's cash-flow behavior rather than a business-only underwriting workflow.

### Money uses decimal storage

Transaction amounts use PostgreSQL `Numeric(12,2)` and Python `Decimal`.

Reason: binary floating-point values cannot represent many currency values exactly.

### Amount and direction are separate

`Transaction.amount` is always positive.

A direction enum identifies whether the transaction is a deposit or withdrawal.

Reason: this avoids mixing signed-value conventions and makes the meaning of each transaction explicit.

### Direction and category use enums

Direction and category values are constrained by the database model.

Reason: invalid values should be rejected near the data boundary instead of reaching the scoring engine.

### Transaction categories have different roles

Current categories:

```text
income
recurring_expense
transfer
fee
other
```

- Transfers are excluded from scoring calculations.
- One-time spending belongs in `other`, not `recurring_expense`.
- Fees are treated as overdraft or NSF events in the current seed data.

The project assigns categories directly in synthetic data. A production system would depend on a bank-data provider or a separate categorization pipeline.

### Account/date index

A composite index on `(account_id, date)` supports the main transaction query over a date window.

## 6. Infrastructure

### PostgreSQL 18 runs in Docker

The local database uses host port `5433` mapped to container port `5432`.

Reason: port `5432` was already in use on the development machine.

### `create_all` is temporary

The prototype creates tables with SQLAlchemy metadata.

Reason: it kept early development simple.

Known limitation: `create_all` does not provide versioned schema changes. Alembic is the planned migration path.

### Synchronous database access first

The project uses synchronous SQLAlchemy and `psycopg2`.

Reason: the current workload does not justify adding asynchronous database complexity.

### Environment files

- `.env` stores local secrets and is ignored by Git.
- `.env.example` contains placeholders and is committed.
- `.venv`, `venv`, `__pycache__`, and `.pytest_cache` are ignored.

### Dependency snapshot

`requirements.txt` records the installed environment.

Reason: it makes the project easier to rebuild on a similar machine. It is not a guarantee of identical behavior across every operating system and Python version.

## 7. Explanation Agent

### The input is deliberately narrow

The agent receives only qualitative labels derived from the deterministic sub-scores:

```text
strong
moderate
weak
```

Reason: removing information is a stronger control than giving the model extra data and asking it not to use it.

### Structured output validates shape, not truth

The Pydantic model requires:

```text
summary
key_strengths
key_concerns
principal_risk_factors
```

It contains no score or risk-tier field.

The first live test exposed an important limitation: the model followed the required structure but still added unsupported interpretations.

I responded by:

- removing the risk tier from the model input
- removing exact sub-scores from the model input
- passing only qualitative labels
- tightening the grounding instructions

Reason: schema validation proves the output shape. It does not prove that every sentence is supported.

### Production hardening

A future version should provide a deterministic meaning with each signal label.

Example:

```text
Signal: net cash flow ratio
Assessment: weak
Deterministic meaning: qualifying cash outflows exceed or nearly match
qualifying income
```

The scoring layer would select the meaning. The LLM would only rewrite that supplied fact into clearer prose.

In a real lending workflow, principal reason codes should also be selected deterministically. The LLM should not invent or choose legal adverse-action reasons.

## 8. Testing

### Scoring functions are unit tested

Tests cover:

- score-band boundaries
- monthly income grouping
- all four signal calculations
- composite weighting
- risk-tier boundaries
- invalid-data propagation

Reason: each test should prove one behavior and make later calibration safer.

### Explanation tests do not call Anthropic

Pydantic AI's `TestModel` replaces the live provider in automated tests.

```python
models.ALLOW_MODEL_REQUESTS = False
```

acts as a safety brake. A badly mocked test fails instead of making a paid network request.

### Manual end-to-end smoke test

Swagger was used to verify the complete local flow:

```text
HTTP request
-> database query
-> deterministic scoring
-> live Anthropic explanation
-> combined JSON response
```

Reason: unit tests prove isolated behavior. The smoke test proves that the integrated application works.

## 9. Development Notes

### Gaps in auto-increment IDs are normal

An early shell experiment consumed sequence value `1` before the transaction was rolled back.

PostgreSQL sequences do not roll back with the transaction, so the next saved record started at a higher ID.

Reason for documenting it: a missing auto-increment value is expected behavior, not evidence of missing data.

## 10. What Would Change Before Production

Before CashFlowIQ could be used with real borrowers, it would need:

- real bank-data ingestion
- reliable transaction categorization
- outcome-based calibration
- versioned scoring policies
- deterministic reason codes
- authentication and rate limiting
- schema migrations
- audit logging
- provider timeouts and retries
- stronger explanation grounding
- legal, compliance, and fair-lending review

The goal of this prototype is not to hide those gaps. It is to make the architecture clear enough that the next steps are obvious.
