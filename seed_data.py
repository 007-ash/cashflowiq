"""
seed_data.py — synthetic transaction generator for CashFlowIQ.

Two archetypes over a ~90-day window (2026-04-01 .. 2026-07-01):
  - Bob:      small business owner, 30-day cycle, thin margins + a one-time shock (marginal profile)
  - Patricia: stable salaried consumer, comfortably cash-flow positive (strong-approve profile)
  - John:     unstable gig economy and contract worker consumer, spends more than they earn (negative profile)

Amounts/dates are explicit (no RNG) -> reproducible by construction.
"""

from datetime import date
from decimal import Decimal

from db import Session
from models import Customer, BankAccount, Transaction, Direction, Category


def add_txn(session, account_id, d, amount, direction, category, description):
    """Stage one transaction. amount is a string -> Decimal (never float for money)."""
    session.add(Transaction(
        account_id=account_id,
        date=d,
        amount=Decimal(amount),
        direction=direction,
        category=category,
        description=description,
    ))


with Session() as session:
    # ---------------------------------------------------------------
    # Bob - small business owner, 30-day cycle. Thin margins + June shock.
    # ---------------------------------------------------------------
    bob = Customer(name="Bob")
    session.add(bob)
    session.flush()                      # assigns bob.id
    bob_acct = BankAccount(customer_id=bob.id, account_number="123456789")
    session.add(bob_acct)
    session.flush()                      # assigns bob_acct.id

    # revenue: $10,000 on the 30th of each month
    for m in (4, 5, 6):
        add_txn(session, bob_acct.id, date(2026, m, 30), "10000.00",
                Direction.deposit, Category.income, "income")

    # payroll: $2,000 to employees on the 1st and 15th
    for d in [date(2026, m, day) for m in (4, 5, 6) for day in (1, 15)] + [date(2026, 7, 1)]:
        add_txn(session, bob_acct.id, d, "2000.00",
                Direction.withdrawal, Category.recurring_expense, "paying employees")

    # overhead: $4,000 on the 1st
    for d in [date(2026, m, 1) for m in (4, 5, 6, 7)]:
        add_txn(session, bob_acct.id, d, "4000.00",
                Direction.withdrawal, Category.recurring_expense, "overhead")

    # one-time shock: leaky pipe on 6/3 - NOT recurring, so category = other
    add_txn(session, bob_acct.id, date(2026, 6, 3), "1500.00",
            Direction.withdrawal, Category.other, "unexpected expense")

    session.commit()

    # ---------------------------------------------------------------
    # Patricia - stable salaried consumer. Comfortably positive.
    # ---------------------------------------------------------------
    patricia = Customer(name="Patricia")
    session.add(patricia)
    session.flush()
    pat_acct = BankAccount(customer_id=patricia.id, account_number="987654321")
    session.add(pat_acct)
    session.flush()

    # biweekly payroll: $2,900 on the 1st and 15th
    for d in [date(2026, m, day) for m in (4, 5, 6) for day in (1, 15)] + [date(2026, 7, 1)]:
        add_txn(session, pat_acct.id, d, "2900.00",
                Direction.deposit, Category.income, "payroll")

    # rent: fixed $2,000, mostly on the 1st, late in May (the 4th) - tests date jitter
    for d in (date(2026, 4, 1), date(2026, 5, 4), date(2026, 6, 1)):
        add_txn(session, pat_acct.id, d, "2000.00",
                Direction.withdrawal, Category.recurring_expense, "rent")

    # utilities: flat $150 monthly, same payee
    for m in (4, 5, 6):
        add_txn(session, pat_acct.id, date(2026, m, 5), "150.00",
                Direction.withdrawal, Category.recurring_expense, "utilities")

    # credit-card payment (subscriptions etc.): $400 end of month
    for m in (4, 5, 6):
        add_txn(session, pat_acct.id, date(2026, m, 30), "400.00",
                Direction.withdrawal, Category.recurring_expense, "credit card payment")

    # transfer to savings: $100 end of month - EXCLUDED from income/expense signals
    for m in (4, 5, 6):
        add_txn(session, pat_acct.id, date(2026, m, 30), "100.00",
                Direction.withdrawal, Category.transfer, "savings")

    session.commit()

    # ---------------------------------------------------------------
    # John - unstable gig economy consumer. He works on contract work and does Uber. Spends more than they earn.
    # ---------------------------------------------------------------
    john = Customer(name="John")
    session.add(john)
    session.flush()
    john_acct = BankAccount(customer_id=john.id, account_number="543216789")
    session.add(john_acct)
    session.flush()

    # app and contract pay out
    gig_payments = [
        (date(2026, 4, 3), "800.00"),
        (date(2026, 4, 10), "600.00"),
        (date(2026, 4, 17), "250.00"),
        (date(2026, 4, 29), "1200.00"),
        (date(2026, 5, 1), "800.00"),
        (date(2026, 5, 15), "300.00"),
        (date(2026, 5, 22), "1000.00"),
        (date(2026, 5, 30), "870.00"),
        (date(2026, 6, 5), "400.00"),
        (date(2026, 6, 12), "700.00"),
        (date(2026, 6, 21), "1160.00"),
        (date(2026, 6, 28), "800.00"),
    ]
    for d, amt in gig_payments:
        add_txn(session, john_acct.id, d, amt, Direction.deposit,
                Category.income, "contract work")

        # rent: fixed $2,500, always late - tests date jitter
    for d in (date(2026, 4, 7), date(2026, 5, 5), date(2026, 6, 8)):
        add_txn(session, john_acct.id, d, "2500.00",
                Direction.withdrawal, Category.recurring_expense, "rent")

        # utilities: flat $550 monthly, same payee
    for m in (4, 5, 6):
        add_txn(session, john_acct.id, date(2026, m, 5), "550.00",
                Direction.withdrawal, Category.recurring_expense, "utilities")

        # credit-card payments on specific dates
    for d in (date(2026, 4, 21), date(2026, 5, 28), date(2026, 7, 8)):
        add_txn(session, john_acct.id, d, "500.00",
                Direction.withdrawal, Category.recurring_expense, "credit card payment")

        # overdraft fees
    for d in (date(2026, 4, 22), date(2026, 5, 30), date(2026, 7, 9)):
        add_txn(session, john_acct.id, d, "50.00",
                Direction.withdrawal, Category.fee, "overdraft fee")

        # one-time tax return deposit on 2026-04-15 - tests income spike
    add_txn(session, john_acct.id, date(2026, 4, 15), "2000.00",
            Direction.deposit, Category.other, "tax return")
    session.commit()
