import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic_ai.exceptions import AgentRunError
from sqlalchemy import select
from sqlalchemy.orm import Session

from dependency import get_db
from explanation_agent import explain
from metrics import score_account
from models import BankAccount, Customer, Transaction

router = APIRouter(tags=["reports"])

WINDOW_START = date(2026, 4, 1)
WINDOW_END = date(2026, 7, 1)  # Exclusive


logger = logging.getLogger(__name__)


@router.post("/customers/{customer_id}/reports", status_code=200)
def create_customer_report(customer_id: int, db: Session = Depends(get_db)):
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    transactions = db.scalars(
        select(Transaction)
        .join(BankAccount)
        .where(
            BankAccount.customer_id == customer_id,
            Transaction.date >= WINDOW_START,
            Transaction.date < WINDOW_END,
        )
    ).all()
    try:
        report = score_account(transactions)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        explanation = explain(report)
    except AgentRunError:
        logger.exception("Explanation generation failed")
        report["explanation"] = None
        report["explanation_status"] = "unavailable"
    else:
        report["explanation"] = explanation.model_dump()
        report["explanation_status"] = "available"

    return report
