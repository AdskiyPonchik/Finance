from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import datetime, date
from sqlmodel import Session, select
from pydantic import BaseModel
from typing import List, Optional

from app.core.database import get_session
from app.core.models import Transaction, User, Category, CategoryType
from app.core.auth import create_access_token, get_current_user, get_password_hash, verify_password
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
