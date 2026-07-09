from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from dependency import get_db
from models import Customer, BankAccount
from schemas import BankAccountRead, BankAccountCreate
from sqlalchemy import select

router = APIRouter(tags=["bank accounts"])


@router.get("/bank_accounts/{account_id}", response_model=BankAccountRead)
def read_bank_account(account_id: int, db: Session = Depends(get_db)):
    account = db.get(BankAccount, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Bank account not found")
    return account


@router.get("/bank_accounts", response_model=list[BankAccountRead])
def list_bank_accounts(db: Session = Depends(get_db)):
    bank_accounts = db.scalars(select(BankAccount)).all()
    return bank_accounts


@router.post("/customers/{customer_id}/bank_accounts", response_model=BankAccountRead, status_code=201)
def create_bank_account(customer_id: int, bank_account: BankAccountCreate, db: Session = Depends(get_db)):
    if db.get(Customer, customer_id) is None:
        raise HTTPException(404, detail="Customer not found")
    bank_account_obj = BankAccount(
        customer_id=customer_id, account_number=bank_account.account_number)
    db.add(bank_account_obj)
    db.commit()
    db.refresh(bank_account_obj)
    return bank_account_obj
