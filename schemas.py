from decimal import Decimal
from datetime import date
from pydantic import BaseModel, ConfigDict
from models import Direction, Category
# a transaction can't exist without an account, so I nested it under its account — the URL itself expresses the ownership


class CustomerCreate(BaseModel):
    name: str


class CustomerRead(BaseModel):
    id: int
    name: str
    model_config = ConfigDict(from_attributes=True)


class BankAccountCreate(BaseModel):
    # customer_id comes from the URL path on create; returned in read
    account_number: str


class BankAccountRead(BaseModel):
    id: int
    customer_id: int
    account_number: str
    model_config = ConfigDict(from_attributes=True)


class TransactionCreate(BaseModel):
    # account_id comes from the URL path on create; returned in read
    date: date
    amount: Decimal
    direction: Direction
    category: Category
    description: str


class TransactionRead(BaseModel):
    id: int
    account_id: int
    date: date
    amount: Decimal
    direction: Direction
    category: Category
    description: str
    model_config = ConfigDict(from_attributes=True)
