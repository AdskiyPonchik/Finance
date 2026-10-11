from datetime import date, datetime, timedelta

from sqlalchemy import case, func
from sqlmodel import Session, select

from app.core.models import Category, CategoryType, Transaction


def calculate_balance(session: Session, user_id: int) -> dict[str, int]:
    liquid, raw_vault = session.exec(
        select(
            func.coalesce(func.sum(Transaction.amount), 0),
            func.coalesce(func.sum(case(
                (Category.type == CategoryType.VAULT, Transaction.amount), else_=0
            )), 0),
        )
        .select_from(Transaction).join(Category)
        .where(Transaction.owner_id == user_id)
    ).one()
    vault = -int(raw_vault)
    return {"liquid": int(liquid), "vault": vault, "net_worth": int(liquid) + vault}


def calculate_cashflow(session: Session, user_id: int, start_date: date, end_date: date):
    if start_date > end_date:
        raise ValueError("start_date must not be after end_date")
    start = datetime.combine(start_date, datetime.min.time())
    end = datetime.combine(end_date, datetime.max.time())

    opening = session.exec(
        select(Category.type, func.sum(Transaction.amount))
        .select_from(Transaction).join(Category)
        .where(Transaction.owner_id == user_id, Transaction.date < start)
        .group_by(Category.type)
    ).all()
    opening_by_type = {kind: int(amount) for kind, amount in opening}
    liquid_opening = sum(opening_by_type.values())
    vault_opening = -opening_by_type.get(CategoryType.VAULT, 0)

    income, expense, deposit, withdraw = session.exec(
        select(
            func.coalesce(func.sum(case(
                (Category.type == CategoryType.INCOME, Transaction.amount), else_=0
            )), 0),
            func.coalesce(func.sum(case(
                (Category.type == CategoryType.EXPENSE, Transaction.amount), else_=0
            )), 0),
            func.coalesce(func.sum(case(
                ((Category.type == CategoryType.VAULT) & (Transaction.amount < 0),
                 -Transaction.amount), else_=0
            )), 0),
            func.coalesce(func.sum(case(
                ((Category.type == CategoryType.VAULT) & (Transaction.amount > 0),
                 -Transaction.amount), else_=0
            )), 0),
        )
        .select_from(Transaction).join(Category)
        .where(Transaction.owner_id == user_id,
               Transaction.date >= start, Transaction.date <= end)
    ).one()
    income, expense, deposit, withdraw = map(int, (income, expense, deposit, withdraw))
    vault_net = deposit + withdraw
    liquid_net = income + expense - vault_net
    return {
        "period": {"start": start_date, "end": end_date},
        "liquid": {
            "opening": liquid_opening, "income": income, "expense": expense,
            "net_flow": liquid_net, "closing": liquid_opening + liquid_net,
        },
        "vault": {
            "opening": vault_opening, "deposit": deposit, "withdraw": withdraw,
            "closing": vault_opening + vault_net,
        },
    }


def get_heatmap_data(session: Session, user_id: int) -> dict[str, int]:
    rows = session.exec(
        select(func.date(Transaction.date), func.count(Transaction.id))
        .where(Transaction.owner_id == user_id)
        .group_by(func.date(Transaction.date))
    ).all()
    return {str(day): int(count) for day, count in rows}


def get_expense_breakdown(session: Session, user_id: int):
    total = (-func.sum(Transaction.amount)).label("total")
    rows = session.exec(
        select(Category.id, Category.name, Category.color, total)
        .select_from(Transaction).join(Category)
        .where(Transaction.owner_id == user_id, Category.type == CategoryType.EXPENSE)
        .group_by(Category.id, Category.name, Category.color)
        .order_by(total.desc())
    ).all()
    return [{"category_id": category_id, "category_name": name,
             "category_color": color, "total": int(amount)}
            for category_id, name, color, amount in rows]


def get_activity_data(session: Session, user_id: int, today: date) -> dict[str, int]:
    rows = session.exec(
        select(func.date(Transaction.date), func.sum(func.abs(Transaction.amount)))
        .where(
            Transaction.owner_id == user_id,
            Transaction.date >= datetime.combine(today - timedelta(days=365), datetime.min.time()),
            Transaction.date <= datetime.combine(today, datetime.max.time()),
        )
        .group_by(func.date(Transaction.date))
    ).all()
    return {str(day): int(amount or 0) for day, amount in rows}

