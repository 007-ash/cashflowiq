
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from dependency import get_db
from models import BankAccount, Transaction
from schemas import TransactionRead, TransactionCreate
from sqlalchemy import select

router = APIRouter(tags=["transactions"])


@router.get("/transactions/{transaction_id}", response_model=TransactionRead)
def read_transaction(transaction_id: int, db: Session = Depends(get_db)):
    transaction = db.get(Transaction, transaction_id)
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction


@router.get("/transactions", response_model=list[TransactionRead])
def list_transactions(db: Session = Depends(get_db)):
    transactions = db.scalars(select(Transaction)).all()
    return transactions


@router.post("/accounts/{account_id}/transactions", response_model=TransactionRead, status_code=201)
def create_transactions(account_id: int, transaction: TransactionCreate, db: Session = Depends(get_db)):
    if db.get(BankAccount, account_id) is None:
        raise HTTPException(404, detail="Bank account not found")
    transaction_obj = Transaction(
        account_id=account_id, **transaction.model_dump())
    db.add(transaction_obj)
    db.commit()
    db.refresh(transaction_obj)
    return transaction_obj
