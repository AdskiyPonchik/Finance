from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.api.analytics import (
    calculate_balance, calculate_cashflow, get_activity_data, get_expense_breakdown, get_heatmap_data,
)
from app.api.schemas import (
    Balance, CashflowResponse, CategoryCreate, CategoryRead, ExpenseBreakdownItem,
    PaginatedTransactionResponse, RecurringTransactionCreate, RecurringTransactionRead,
    TransactionCreate, TransactionRead, TransactionUpdate, UserRead,
)
from app.api.utils import process_recurring_transactions, validate_amount
from app.core.auth import create_access_token, get_current_user, get_password_hash, verify_password
from app.core.config import business_today
from app.core.database import get_session
from app.core.models import Category, RecurringTransaction, Transaction, User

router = APIRouter()
auth_router = APIRouter()
users_router = APIRouter()
_DUMMY_HASH = get_password_hash("unused-login-timing-password")


def owned_category(session: Session, category_id: int, user_id: int) -> Category:
    category = session.exec(select(Category).where(
        Category.id == category_id, Category.owner_id == user_id,
    )).first()
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


def check_amount(amount: int, category: Category):
    try:
        validate_amount(amount, category.type)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error))


def transaction_response(transaction: Transaction, category: Category) -> TransactionRead:
    return TransactionRead(
        id=transaction.id, title=transaction.title, amount=transaction.amount,
        date=transaction.date.date(), category_id=category.id,
        category_name=category.name, category_type=category.type, category_color=category.color,
    )


@auth_router.post("/token")
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session),
):
    user = session.exec(select(User).where(User.username == form_data.username)).first()
    password_ok = verify_password(form_data.password, user.hashed_password if user else _DUMMY_HASH)
    if user is None or not password_ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"access_token": create_access_token({"sub": user.username}), "token_type": "bearer"}


@users_router.get("/me", response_model=UserRead)
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/transactions/", response_model=TransactionRead)
def create_transaction(
    tx_data: TransactionCreate, current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    category = owned_category(session, tx_data.category_id, current_user.id)
    check_amount(tx_data.amount, category)
    transaction = Transaction(
        title=tx_data.title, amount=tx_data.amount,
        date=datetime.combine(tx_data.date, datetime.min.time()),
        owner_id=current_user.id, category_id=category.id,
    )
    session.add(transaction)
    session.commit()
    session.refresh(transaction)
    return transaction_response(transaction, category)


@router.put("/transactions/{transaction_id}", response_model=TransactionRead)
def update_transaction(
    transaction_id: int, tx_data: TransactionUpdate,
    current_user: User = Depends(get_current_user), session: Session = Depends(get_session),
):
    transaction = session.exec(select(Transaction).where(
        Transaction.id == transaction_id, Transaction.owner_id == current_user.id,
    )).first()
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    category = owned_category(session, tx_data.category_id, current_user.id)
    check_amount(tx_data.amount, category)
    transaction.title = tx_data.title
    transaction.amount = tx_data.amount
    transaction.date = datetime.combine(tx_data.date, datetime.min.time())
    transaction.category_id = category.id
    session.add(transaction)
    session.commit()
    session.refresh(transaction)
    return transaction_response(transaction, category)


@router.delete("/transactions/{transaction_id}", status_code=204)
def delete_transaction(
    transaction_id: int, current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    transaction = session.exec(select(Transaction).where(
        Transaction.id == transaction_id, Transaction.owner_id == current_user.id,
    )).first()
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    session.delete(transaction)
    session.commit()


@router.get("/transactions/", response_model=PaginatedTransactionResponse)
def get_transactions(
    current_user: User = Depends(get_current_user), session: Session = Depends(get_session),
    offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100),
):
    total = session.exec(select(func.count()).select_from(Transaction).where(
        Transaction.owner_id == current_user.id,
    )).one()
    rows = session.exec(
        select(Transaction, Category).join(Category)
        .where(Transaction.owner_id == current_user.id)
        .order_by(Transaction.date.desc(), Transaction.id.desc())
        .offset(offset).limit(limit)
    ).all()
    return PaginatedTransactionResponse(
        total=total, items=[transaction_response(tx, cat) for tx, cat in rows],
    )


@router.get("/balance/", response_model=Balance)
def get_balance(
    current_user: User = Depends(get_current_user), session: Session = Depends(get_session),
):
    return calculate_balance(session, current_user.id)


@router.post("/categories/", response_model=CategoryRead, status_code=201)
def create_category(
    category_data: CategoryCreate, current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    category = Category(**category_data.model_dump(), owner_id=current_user.id)
    session.add(category)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="Category with this name already exists")
    session.refresh(category)
    return category


@router.get("/categories/", response_model=list[CategoryRead])
def get_categories(
    current_user: User = Depends(get_current_user), session: Session = Depends(get_session),
):
    return session.exec(select(Category).where(Category.owner_id == current_user.id)).all()


@router.delete("/categories/{category_id}", status_code=204)
def delete_category(
    category_id: int, current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    category = owned_category(session, category_id, current_user.id)
    used_by_transaction = session.exec(select(Transaction.id).where(
        Transaction.category_id == category_id,
    ).limit(1)).first()
    used_by_recurring = session.exec(select(RecurringTransaction.id).where(
        RecurringTransaction.category_id == category_id,
    ).limit(1)).first()
    if used_by_transaction is not None or used_by_recurring is not None:
        raise HTTPException(status_code=409, detail="Category is used by transactions or subscriptions")
    session.delete(category)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="Category is still in use")


@router.post("/recurring/", response_model=RecurringTransactionRead, status_code=201)
def create_recurring_transaction(
    recurring_data: RecurringTransactionCreate, current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    category = owned_category(session, recurring_data.category_id, current_user.id)
    if category.type.value != recurring_data.type:
        raise HTTPException(status_code=422, detail="Subscription type must match its category")
    check_amount(recurring_data.amount, category)
    recurring = RecurringTransaction(**recurring_data.model_dump(), owner_id=current_user.id)
    session.add(recurring)
    session.commit()
    session.refresh(recurring)
    return recurring


@router.post("/recurring/process")
def process_recurring(
    current_user: User = Depends(get_current_user), session: Session = Depends(get_session),
):
    try:
        created = process_recurring_transactions(session, current_user.id)
        session.commit()
    except ValueError as error:
        session.rollback()
        raise HTTPException(status_code=409, detail=str(error))
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="Conflicting subscription change; retry the request")
    return {"created": created}


@router.get("/recurring/", response_model=list[RecurringTransactionRead])
def get_recurring_transactions(
    current_user: User = Depends(get_current_user), session: Session = Depends(get_session),
):
    return session.exec(select(RecurringTransaction).where(
        RecurringTransaction.owner_id == current_user.id,
    )).all()


@router.delete("/recurring/{recurring_id}", status_code=204)
def delete_recurring_transaction(
    recurring_id: int, current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    recurring = session.exec(select(RecurringTransaction).where(
        RecurringTransaction.id == recurring_id, RecurringTransaction.owner_id == current_user.id,
    )).first()
    if recurring is None:
        raise HTTPException(status_code=404, detail="Recurring transaction not found")
    session.delete(recurring)
    session.commit()


@router.get("/analytics/cashflow", response_model=CashflowResponse)
def get_cashflow_analytics(
    start_date: date, end_date: date, current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    if start_date > end_date:
        raise HTTPException(status_code=422, detail="start_date must not be after end_date")
    return calculate_cashflow(session, current_user.id, start_date, end_date)


@router.get("/analytics/heatmap", response_model=dict[str, int])
def get_heatmap_analytics(
    current_user: User = Depends(get_current_user), session: Session = Depends(get_session),
):
    return get_heatmap_data(session, current_user.id)


@router.get("/analytics/expenses", response_model=list[ExpenseBreakdownItem])
def get_expenses(
    current_user: User = Depends(get_current_user), session: Session = Depends(get_session),
):
    return get_expense_breakdown(session, current_user.id)


@router.get("/analytics/activity", response_model=dict[str, int])
def get_activity_map(
    current_user: User = Depends(get_current_user), session: Session = Depends(get_session),
):
    return get_activity_data(session, current_user.id, business_today())