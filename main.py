from fastapi import FastAPI
from routers import customer, bank_account, transaction, reports

app = FastAPI()
app.include_router(customer.router)
app.include_router(bank_account.router)
app.include_router(transaction.router)
app.include_router(reports.router)
