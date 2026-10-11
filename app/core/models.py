from datetime import date as Date, datetime
from enum import Enum

from sqlalchemy import BigInteger, CheckConstraint, Index, UniqueConstraint
from sqlmodel import Field, Relationship, SQLModel

from app.core.config import business_today


class CategoryType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"
    VAULT = "vault"


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    hashed_password: str

    transactions: list["Transaction"] = Relationship(back_populates="owner")
    categories: list["Category"] = Relationship(back_populates="owner")
    recurring_transactions: list["RecurringTransaction"] = Relationship(back_populates="owner")


class Category(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("name", "owner_id", name="unique_category_for_user"),)
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    type: CategoryType
    color: str = Field(default="#808080")
    owner_id: int = Field(foreign_key="user.id")
    owner: User = Relationship(back_populates="categories")
    transactions: list["Transaction"] = Relationship(back_populates="category")
    recurring_transactions: list["RecurringTransaction"] = Relationship(back_populates="category")


class Transaction(SQLModel, table=True):
    __table_args__ = (
        CheckConstraint("amount <> 0", name="ck_transaction_amount_nonzero"),
        Index("ix_transaction_owner_date_id", "owner_id", "date", "id"),
    )
    id: int | None = Field(default=None, primary_key=True)
    title: str | None = Field(default=None)
    amount: int = Field(sa_type=BigInteger)
    date: datetime = Field(default_factory=datetime.now, index=True)
    owner_id: int = Field(foreign_key="user.id")
    owner: User = Relationship(back_populates="transactions")
    category_id: int = Field(foreign_key="category.id")
    category: Category = Relationship(back_populates="transactions")


class RecurringTransaction(SQLModel, table=True):
    __table_args__ = (
        CheckConstraint("amount <> 0", name="ck_recurring_amount_nonzero"),
        CheckConstraint("day_of_month BETWEEN 1 AND 31", name="ck_recurring_day"),
        CheckConstraint("type IN ('income', 'expense')", name="ck_recurring_type"),
        Index("ix_recurring_owner_active", "owner_id", "is_active"),
    )
    id: int | None = Field(default=None, primary_key=True)
    title: str
    amount: int = Field(sa_type=BigInteger)
    category_id: int = Field(foreign_key="category.id")
    type: str
    day_of_month: int
    created_on: Date = Field(default_factory=business_today)
    last_run_date: Date | None = None
    is_active: bool = Field(default=True)
    owner_id: int = Field(foreign_key="user.id")
    owner: User = Relationship(back_populates="recurring_transactions")
    category: Category = Relationship(back_populates="recurring_transactions")


class RecurringOccurrence(SQLModel, table=True):
    """A durable receipt: one charge per subscription and scheduled date."""
    recurring_id: int = Field(
        foreign_key="recurringtransaction.id", ondelete="CASCADE", primary_key=True
    )
    scheduled_date: Date = Field(primary_key=True)