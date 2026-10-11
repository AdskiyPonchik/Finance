from datetime import date as Date
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from app.core.models import CategoryType

def nonzero(value: int) -> int:
    if value == 0:
        raise ValueError("Amount must not be zero.")
    return value


Amount = Annotated[
    int, Field(strict=True, ge=-(2**53) + 1, le=2**53 - 1), AfterValidator(nonzero)
]


class InputModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class TransactionCreate(InputModel):
    title: str | None = Field(default=None, max_length=255)
    amount: Amount
    date: Date
    category_id: int = Field(strict=True, gt=0)


class TransactionUpdate(TransactionCreate):
    pass


class TransactionRead(BaseModel):
    id: int
    title: str | None
    amount: int
    date: Date
    category_id: int
    category_name: str
    category_type: CategoryType
    category_color: str


class PaginatedTransactionResponse(BaseModel):
    total: int
    items: list[TransactionRead]


class Balance(BaseModel):
    liquid: int
    vault: int
    net_worth: int


class ExpenseBreakdownItem(BaseModel):
    category_id: int
    category_name: str
    category_color: str
    total: int


class CategoryCreate(InputModel):
    name: str = Field(min_length=1, max_length=100)
    color: str = Field(pattern=r"^#[0-9a-fA-F]{6}$")
    type: CategoryType


class CategoryRead(BaseModel):
    id: int
    name: str
    type: CategoryType
    color: str


class UserRead(BaseModel):
    id: int
    username: str


class RecurringTransactionCreate(InputModel):
    title: str = Field(min_length=1, max_length=255)
    amount: Amount
    category_id: int = Field(strict=True, gt=0)
    type: Literal["income", "expense"]
    day_of_month: int = Field(strict=True, ge=1, le=31)


class RecurringTransactionRead(BaseModel):
    id: int
    title: str
    amount: int
    category_id: int
    type: str
    day_of_month: int
    last_run_date: Date | None
    is_active: bool


class CashflowPeriod(BaseModel):
    start: Date
    end: Date


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