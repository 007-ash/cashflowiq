from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from dependency import get_db
from models import Customer
from schemas import CustomerRead, CustomerCreate
from sqlalchemy import select

router = APIRouter(tags=["customers"])


@router.get("/customers/{customer_id}", response_model=CustomerRead)
def read_customer(customer_id: int, db: Session = Depends(get_db)):
    customer = db.get(Customer, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.get("/customers", response_model=list[CustomerRead])
def list_customers(db: Session = Depends(get_db)):
    customers = db.scalars(select(Customer)).all()
    return customers


@router.post("/customers", response_model=CustomerRead, status_code=201)
def create_customer(customer: CustomerCreate, db: Session = Depends(get_db)):
    customer_obj = Customer(name=customer.name)
    db.add(customer_obj)
    db.commit()
    db.refresh(customer_obj)
    return customer_obj
