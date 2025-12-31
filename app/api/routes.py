from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import datetime, date
from sqlmodel import Session, select, func
from sqlalchemy import func
from pydantic import BaseModel
from typing import List, Optional, Dict

from app.core.database import get_session
from app.core.models import Transaction, User, Category, CategoryType, RecurringTransaction
from app.core.auth import create_access_token, get_current_user, get_password_hash, verify_password
from app.api.utils import process_recurring_transactions
from app.api.analytics import calculate_cashflow, get_heatmap_data
from datetime import timedelta

# --- Routers ---
router = APIRouter()
auth_router = APIRouter()
users_router = APIRouter()

# --- Pydantic Models for API ---
class TransactionBase(BaseModel):
    title: Optional[str] = None
    amount: int
    date: date
    category_id: int

class TransactionCreate(TransactionBase):
    pass

class TransactionUpdate(TransactionBase):
    pass

class TransactionRead(BaseModel):
    id: int
    title: Optional[str]
    amount: int
    date: date
    category_id: int
    category_name: str
    category_type: CategoryType
    category_color: str

class Balance(BaseModel):
    liquid: int
    vault: int
    net_worth: int

class CategoryCreate(BaseModel):
    name: str
    color: str
    type: CategoryType

class CategoryRead(BaseModel):
    id: int
    name: str
    type: CategoryType
    color: str

class UserRead(BaseModel):
    id: int
    username: str

class RecurringTransactionCreate(BaseModel):
    title: str
    amount: int
    category_id: int
    type: str
    day_of_month: int

class RecurringTransactionRead(BaseModel):
    id: int
    title: str
    amount: int
    category_id: int
    type: str
    day_of_month: int
    last_run_date: Optional[date]
    is_active: bool

class CashflowPeriod(BaseModel):
    start: date
    end: date

class CashflowLiquid(BaseModel):
    opening: int
    income: int
    expense: int
    net_flow: int
    closing: int

class CashflowVault(BaseModel):
    opening: int
    deposit: int
    withdraw: int
    closing: int

class CashflowResponse(BaseModel):
    period: CashflowPeriod
    liquid: CashflowLiquid
    vault: CashflowVault

# --- Authentication Endpoints ---
@auth_router.post("/token")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.username == form_data.username)).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password", headers={"WWW-Authenticate": "Bearer"})
    
    access_token = create_access_token(data={"sub": user.username}, expires_delta=timedelta(minutes=30))
    return {"access_token": access_token, "token_type": "bearer"}

# --- User Endpoints ---
@users_router.get("/me", response_model=UserRead)
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

# --- Transaction Endpoints ---
@router.post("/transactions/", response_model=TransactionRead)
def create_transaction(
    tx_data: TransactionCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    category = session.exec(select(Category).where(Category.id == tx_data.category_id, Category.owner_id == current_user.id)).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    transaction = Transaction(
        title=tx_data.title,
        amount=tx_data.amount,
        date=datetime.combine(tx_data.date, datetime.min.time()),
        owner_id=current_user.id,
        category_id=category.id
    )
    session.add(transaction)
    session.commit()
    session.refresh(transaction)

    return TransactionRead(
        id=transaction.id,
        title=transaction.title,
        amount=transaction.amount,
        date=transaction.date.date(),
        category_id=category.id,
        category_name=category.name,
        category_type=category.type,
        category_color=category.color
    )

@router.put("/transactions/{transaction_id}", response_model=TransactionRead)
def update_transaction(
    transaction_id: int,
    tx_data: TransactionUpdate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    transaction = session.exec(select(Transaction).where(Transaction.id == transaction_id, Transaction.owner_id == current_user.id)).first()
    if not transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

    category = session.exec(select(Category).where(Category.id == tx_data.category_id, Category.owner_id == current_user.id)).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    transaction.title = tx_data.title
    transaction.amount = tx_data.amount
    transaction.date = datetime.combine(tx_data.date, datetime.min.time())
    transaction.category_id = category.id
    
    session.add(transaction)
    session.commit()
    session.refresh(transaction)

    return TransactionRead(
        id=transaction.id,
        title=transaction.title,
        amount=transaction.amount,
        date=transaction.date.date(),
        category_id=category.id,
        category_name=category.name,
        category_type=category.type,
        category_color=category.color
    )

@router.delete("/transactions/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
        transaction_id: int,
        current_user: User = Depends(get_current_user),
        session: Session = Depends(get_session)
):
    transaction = session.exec(select(Transaction).where(Transaction.id == transaction_id, Transaction.owner_id == current_user.id)).first()
    if not transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")
    session.delete(transaction)
    session.commit()
    return

@router.get("/transactions/", response_model=List[TransactionRead])
def get_transactions(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    # Check for recurring transactions
    process_recurring_transactions(session, current_user.id)

    statement = select(Transaction, Category).join(Category).where(Transaction.owner_id == current_user.id).order_by(Transaction.date.desc())
    results = session.exec(statement).all()
    
    return [
        TransactionRead(
            id=tx.id,
            title=tx.title,
            amount=tx.amount,
            date=tx.date.date(),
            category_id=cat.id,
            category_name=cat.name,
            category_type=cat.type,
            category_color=cat.color
        ) for tx, cat in results
    ]

@router.get("/balance/", response_model=Balance)
def get_balance(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    # Check for recurring transactions
    process_recurring_transactions(session, current_user.id)

    statement = select(Transaction.amount, Category.type).join(Category).where(Transaction.owner_id == current_user.id)
    transactions = session.exec(statement).all()
    liquid_balance = sum(t[0] for t in transactions if t[1] != CategoryType.VAULT)
    vault_balance = sum(t[0] for t in transactions if t[1] == CategoryType.VAULT)
    net_worth = liquid_balance + vault_balance
    return Balance(liquid=liquid_balance, vault=vault_balance, net_worth=net_worth)

# --- Category Management Endpoints ---
@router.post("/categories/", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(
    category_data: CategoryCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    existing_category = session.exec(select(Category).where(Category.name == category_data.name, Category.owner_id == current_user.id)).first()
    if existing_category:
        raise HTTPException(status_code=400, detail="Category with this name already exists")
    new_category = Category(name=category_data.name, color=category_data.color, type=category_data.type, owner_id=current_user.id)
    session.add(new_category)
    session.commit()
    session.refresh(new_category)
    return new_category

@router.get("/categories/", response_model=List[CategoryRead])
def get_categories(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    categories = session.exec(select(Category).where(Category.owner_id == current_user.id)).all()
    return categories

@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    category = session.exec(select(Category).where(Category.id == category_id, Category.owner_id == current_user.id)).first()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    
    # Check if category is in use
    transaction = session.exec(select(Transaction).where(Transaction.category_id == category_id)).first()
    if transaction:
        raise HTTPException(status_code=400, detail="Cannot delete category: it is currently in use by one or more transactions.")

    session.delete(category)
    session.commit()
    return

# --- Recurring Transaction Endpoints ---
@router.post("/recurring/", response_model=RecurringTransactionRead, status_code=status.HTTP_201_CREATED)
def create_recurring_transaction(
    recurring_data: RecurringTransactionCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    category = session.exec(select(Category).where(Category.id == recurring_data.category_id, Category.owner_id == current_user.id)).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    recurring_transaction = RecurringTransaction(
        title=recurring_data.title,
        amount=recurring_data.amount,
        category_id=category.id,
        type=recurring_data.type,
        day_of_month=recurring_data.day_of_month,
        owner_id=current_user.id
    )
    session.add(recurring_transaction)
    session.commit()
    session.refresh(recurring_transaction)
    return recurring_transaction

@router.get("/recurring/", response_model=List[RecurringTransactionRead])
def get_recurring_transactions(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    recurring_transactions = session.exec(select(RecurringTransaction).where(RecurringTransaction.owner_id == current_user.id)).all()
    return recurring_transactions

@router.delete("/recurring/{recurring_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recurring_transaction(
    recurring_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    recurring_transaction = session.exec(select(RecurringTransaction).where(RecurringTransaction.id == recurring_id, RecurringTransaction.owner_id == current_user.id)).first()
    if not recurring_transaction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recurring transaction not found")
    
    session.delete(recurring_transaction)
    session.commit()
    return

# --- Analytics Endpoints ---
@router.get("/analytics/cashflow", response_model=CashflowResponse)
def get_cashflow_analytics(
    start_date: date,
    end_date: date,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    return calculate_cashflow(session, current_user.id, start_date, end_date)

@router.get("/analytics/heatmap", response_model=Dict[str, int])
def get_heatmap_analytics(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    return get_heatmap_data(session, current_user.id)


@router.get("/analytics/activity", response_model=Dict[str, int])
def get_activity_map(
        current_user: User = Depends(get_current_user),
        session: Session = Depends(get_session)
):
    today = date.today()
    start_date = today - timedelta(days=365)

    # SQLite stores datetime as strings, so func.date() will correctly truncate the time.
    # We group specifically by DAY, ignoring hours and minutes.
    statement = (
        select(func.date(Transaction.date), func.sum(func.abs(Transaction.amount)))
        .where(Transaction.owner_id == current_user.id)
        .where(Transaction.date >= datetime.combine(start_date, datetime.min.time()))
        .group_by(func.date(Transaction.date))
    )

    results = session.exec(statement).all()

    activity_data = {}
    for date_str, amount in results:
        # date_str will be a string 'YYYY-MM-DD' thanks to func.date()
        # amount can be None if there were no transactions (though the where clause should prevent this), default to 0 just in case.
        activity_data[date_str] = int(amount) if amount is not None else 0

    return activity_data
