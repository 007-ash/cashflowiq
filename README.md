# CashFlowIQ

## Problem Statement

> **[Ash — write one paragraph here, in your own words.]**
> This is the anchor for every design decision in the project. Before any feature,
> ask: does this serve the problem stated here? If not, it's building to build.
> (Your domain session assigned you this paragraph — keep it yours; don't let me write it.)

## What It Is

An API that turns raw bank transactions into an auditable **0–100 lending risk score**, with an LLM layer that *explains* the decision but never *makes* it.

## The Domain Problem

Traditional underwriting scores **borrowing history** (credit-bureau data), which fails thin-file / no-file borrowers who may manage money well but have no credit story. CashFlowIQ scores **money behavior** — actual bank-transaction patterns — instead. It complements traditional scores rather than replacing them (it also catches present-tense deterioration that a backward-looking FICO misses).

## Architecture Thesis (the core principle — say this in interviews)

**The deterministic layer decides; the LLM only narrates.** Risk scores are computed by transparent, testable math. The ExplanationAgent (Claude API) takes the *already-computed* score and puts it into words — it never touches the number.

This is a **regulatory** requirement, not a stylistic one: ECOA / Regulation B adverse-action notices require consistent, auditable reasons for a lending decision. An LLM in the decision path can't guarantee that; deterministic math can. **The LLM is nowhere in the scoring.**

## Scoring — the Four Deterministic Signals

1. **Income stability** — coefficient of variation of the income stream
2. **Recurring expense ratio** — recurring outflows relative to income
3. **Overdraft / NSF frequency** — how often the account goes negative / incurs fees
4. **Balance trend** — linear regression over the running balance

Weighted (documented weights) → **0–100 composite score** → risk tier.

### Why 0–100, not CashScore's 0–999

Prism Data's CashScore (0–999) is the output of a **validated statistical model** predicting 12-month default probability, tested against real loan outcomes. CashFlowIQ's 0–100 is a **transparent weighted composite** — deliberately *not* a claim to replicate that validated model. Copying the 0–999 range without the model behind it would be superficial. Naming the difference — "mine is a transparent, auditable composite demonstrating the architecture; theirs is a validated default model" — is a **feature of understanding their product**, not a gap.

## Data Model

`Business → BankAccount → Transaction` (one-to-many chain).
Planned: `Business → UnderwritingReport → Explanation` (1:1 via unique FK).

Design decisions:
- **Money** is `Numeric(12,2)`, never `float` — binary floats can't represent decimal cents exactly and the error accumulates until the ledger won't tie out.
- **Foreign keys live on the many side**, pointing at the one side (a single FK column expresses "one parent per row").
- **`Transaction.amount` is positive**; a `direction` enum (`deposit` / `withdrawal`) carries the sign. **Balance is derived** (deposits − withdrawals), not stored — avoids a stale denormalized field.
- **`Transaction.category`** (enum) labels each transaction so the four signals can be computed: `income`, `recurring_expense`, `transfer`, `fee`, `other`. **Transfers are excluded** from income/expense math so internal journals don't inflate the signals.
- **Composite index on `(account_id, date)`** serves the core metrics query (`WHERE account_id = ? ORDER BY date`).

### Categorization is a documented production gap

In production, an aggregator (Plaid, or Prism's pipeline) supplies transaction categories — that categorization is itself a hard ML/heuristic problem. The synthetic seed data **assigns categories directly**; the categorization engine is **not faked**, it's documented here as a production dependency. (Same principle as ParcelIQ's "no fake geospatial": build the framework that consumes the data, don't fake the hard upstream step.)

## Tech Decisions

- **Sync-first** (`psycopg2`); async deferred until proven necessary.
- **Postgres 18 in Docker** (docker-compose, plus a pgAdmin service).
  - Host port **5433** (`"5433:5432"`) — avoids a collision with a local Postgres 18 install already on 5432. Container-internal port stays 5432.
  - Volume mount **`/var/lib/postgresql`** (not the classic `/var/lib/postgresql/data`) — Postgres 18 changed the data-dir layout; the old mount crash-loops the container.
- **Schema via `create_all`** for now; **Alembic migrations deferred** and documented. (`create_all` can't evolve an existing table — schema changes currently require drop + recreate of the dev DB.)
- **Three-layer architecture**: routers (thin HTTP) → services (pure-function domain logic, unit-tested) → models (SQLAlchemy). `config.py` loads env fail-fast; session-per-request.
- **Secrets** in `.env` (gitignored); `.env.example` committed. `venv/` never committed.
- **Deploy target**: Railway.
- **Reproducible env**: `pip freeze > requirements.txt` so the (disposable) venv can be rebuilt with `pip install -r requirements.txt`.

## Deferred (Deliberately)

Alembic migrations · async · auth / logging / background jobs · human-in-the-loop · real data inputs (Plaid sandbox) · deepened intelligence (more agents / multi-step). Roadmap: Alembic → real data inputs → deepen intelligence → ops.

## Setup

```bash
docker compose up -d                       # Postgres + pgAdmin
python -m venv .venv
.\.venv\Scripts\Activate.ps1               # Windows PowerShell
pip install -r requirements.txt
python -c "from db import engine, Model; import models; Model.metadata.create_all(engine)"
python seed_data.py
```

_A running decision log lives in `decisions.md` (granular "chose X over Y because Z" entries). This README is the front-door summary._