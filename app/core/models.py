from datetime import datetime, date
from enum import Enum
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship, UniqueConstraint


class CategoryType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"
    VAULT = "vault"


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    hashed_password: str

    transactions: List["Transaction"] = Relationship(back_populates="owner")
    categories: List["Category"] = Relationship(back_populates="owner")
    recurring_transactions: List["RecurringTransaction"] = Relationship(back_populates="owner")


class Category(SQLModel, table=True):
    __table_args__ = (UniqueConstraint("name", "owner_id", name="unique_category_for_user"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    type: CategoryType
    color: str = Field(default="#808080")  # Default to gray

    owner_id: int = Field(foreign_key="user.id")
    owner: User = Relationship(back_populates="categories")

    transactions: List["Transaction"] = Relationship(back_populates="category")
    recurring_transactions: List["RecurringTransaction"] = Relationship(back_populates="category")


class Transaction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: Optional[str] = Field(default=None)
    amount: int
    date: datetime = Field(default_factory=datetime.now, index=True)

    owner_id: int = Field(foreign_key="user.id")
    owner: User = Relationship(back_populates="transactions")

    category_id: int = Field(foreign_key="category.id")
    category: Category = Relationship(back_populates="transactions")


class RecurringTransaction(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    amount: int
    category_id: int = Field(foreign_key="category.id")
    type: str  # expense/income
    day_of_month: int
    last_run_date: Optional[date] = None
    is_active: bool = Field(default=True)
    owner_id: int = Field(foreign_key="user.id")

    owner: User = Relationship(back_populates="recurring_transactions")
    category: Category = Relationship(back_populates="recurring_transactions")
