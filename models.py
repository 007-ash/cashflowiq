import enum
from decimal import Decimal
from sqlalchemy import Date, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column
from db import Model
from sqlalchemy import ForeignKey
from datetime import date
from sqlalchemy import Index, Enum


class Customer(Model):
    __tablename__ = 'customer'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64))

    def __repr__(self):
        return f'Customer({self.id}, "{self.name}")'


class BankAccount(Model):
    __tablename__ = 'bank_account'

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customer.id"))
    account_number: Mapped[str] = mapped_column(String(32))

    def __repr__(self):
        return f'BankAccount({self.id}, "{self.account_number}")'

# amount is positive; direction column carries deposit/withdrawal; balance = deposits − withdrawals.


class Direction(enum.Enum):
    deposit = "deposit"
    withdrawal = "withdrawal"


class Category(enum.Enum):
    income = "income"                       # → income stability (CoV)
    recurring_expense = "recurring_expense"  # → recurring expense ratio
    # internal journals — EXCLUDED from income/expense
    transfer = "transfer"
    fee = "fee"                             # overdraft / NSF events → overdraft frequency
    other = "other"                         # discretionary / uncategorized


class Transaction(Model):
    __tablename__ = 'transaction'

    __table_args__ = (
        Index("ix_transaction_account_date", "account_id", "date"),
    )

    account_id: Mapped[int] = mapped_column(ForeignKey("bank_account.id"))
    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[date] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    direction: Mapped[Direction] = mapped_column(Enum(Direction))
    category: Mapped[Category] = mapped_column(Enum(Category))
    description: Mapped[str] = mapped_column(String(128))

    def __repr__(self):
        return f'Transaction({self.id}, {self.amount}, {self.direction}, {self.category}, "{self.description}")'
