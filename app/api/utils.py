from calendar import monthrange
from datetime import date, datetime

from sqlmodel import Session, select

from app.core.config import business_today
from app.core.models import (
    Category, CategoryType, RecurringOccurrence, RecurringTransaction, Transaction,
)


def next_month(month: date) -> date:
    if month.month == 12:
        return date(month.year + 1, 1, 1)
    return date(month.year, month.month + 1, 1)


def due_dates(item: RecurringTransaction, today: date):
    month = item.created_on.replace(day=1)
    if item.last_run_date is not None:
        month = max(month, next_month(item.last_run_date.replace(day=1)))
    while month <= today.replace(day=1):
        day = min(item.day_of_month, monthrange(month.year, month.month)[1])
        scheduled = month.replace(day=day)
        if item.created_on <= scheduled <= today:
            yield scheduled
        month = next_month(month)


def validate_amount(amount: int, category_type: CategoryType):
    if category_type == CategoryType.EXPENSE and amount >= 0:
        raise ValueError("Expense amount must be negative.")
    if category_type == CategoryType.INCOME and amount <= 0:
        raise ValueError("Income amount must be positive.")


def process_recurring_transactions(session: Session, user_id: int, today: date | None = None) -> int:
    """Caller commits/rolls back; PostgreSQL row locks last until that boundary."""
    today = today or business_today()
    items = session.exec(
        select(RecurringTransaction)
        .where(RecurringTransaction.owner_id == user_id, RecurringTransaction.is_active.is_(True))
        .order_by(RecurringTransaction.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).all()
    created = 0
    for item in items:
        category = session.get(Category, item.category_id)
        if (category is None or category.owner_id != user_id
                or category.type.value != item.type):
            raise ValueError(f"Subscription {item.id} has an invalid category or type.")
        validate_amount(item.amount, category.type)
        for scheduled in due_dates(item, today):
            # The receipt survives deleting the generated transaction: it is not charged twice.
            if session.get(RecurringOccurrence, (item.id, scheduled)) is None:
                session.add(RecurringOccurrence(recurring_id=item.id, scheduled_date=scheduled))
                session.add(Transaction(
                    title=item.title, amount=item.amount,
                    date=datetime.combine(scheduled, datetime.min.time()),
                    owner_id=user_id, category_id=item.category_id,
                ))
                created += 1
            item.last_run_date = scheduled
            session.add(item)
    session.flush()
    return created