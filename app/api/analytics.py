from datetime import date, datetime
from typing import Dict, Any
from sqlmodel import Session, select, func
from sqlalchemy import case
from app.core.models import Transaction, Category, CategoryType

def calculate_cashflow(session: Session, user_id: int, start_date: date, end_date: date) -> Dict[str, Any]:
    # Convert dates to datetime for comparison
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())

    # --- 1. Calculate Opening Balance (Liquid & Vault) ---
    # Sum of amounts for all transactions where date < start_date
    opening_statement = (
        select(Category.type, func.sum(Transaction.amount))
        .join(Category)
        .where(Transaction.owner_id == user_id)
        .where(Transaction.date < start_datetime)
        .group_by(Category.type)
    )
    opening_results = session.exec(opening_statement).all()
    
    opening_balances = {
        CategoryType.INCOME: 0,
        CategoryType.EXPENSE: 0,
        CategoryType.VAULT: 0
    }
    for cat_type, amount in opening_results:
        if amount is not None:
            opening_balances[cat_type] = amount

    # Liquid Opening = (Income_Opening + Expense_Opening) - Vault_Opening
    # Vault Opening = Vault_Opening
    
    liquid_opening_val = (opening_balances[CategoryType.INCOME] + opening_balances[CategoryType.EXPENSE]) - opening_balances[CategoryType.VAULT]
    vault_opening_val = opening_balances[CategoryType.VAULT]

    # --- 2. Calculate Period Flows ---
    # Query 1: Income and Expense sums
    inc_exp_statement = (
        select(Category.type, func.sum(Transaction.amount))
        .join(Category)
        .where(Transaction.owner_id == user_id)
        .where(Category.type.in_([CategoryType.INCOME, CategoryType.EXPENSE]))
        .where(Transaction.date >= start_datetime)
        .where(Transaction.date <= end_datetime)
        .group_by(Category.type)
    )
    inc_exp_results = session.exec(inc_exp_statement).all()
    inc_exp_map = {CategoryType.INCOME: 0, CategoryType.EXPENSE: 0}
    for cat_type, amount in inc_exp_results:
        if amount:
            inc_exp_map[cat_type] = amount
            
    # Query 2: Vault split
    vault_split_statement = (
        select(
            func.sum(case((Transaction.amount > 0, Transaction.amount), else_=0)), # Deposit
            func.sum(case((Transaction.amount < 0, Transaction.amount), else_=0))  # Withdraw
        )
        .join(Category)
        .where(Transaction.owner_id == user_id)
        .where(Category.type == CategoryType.VAULT)
        .where(Transaction.date >= start_datetime)
        .where(Transaction.date <= end_datetime)
    )
    vault_split_result = session.exec(vault_split_statement).first()
    vault_deposit = vault_split_result[0] if vault_split_result and vault_split_result[0] else 0
    vault_withdraw = vault_split_result[1] if vault_split_result and vault_split_result[1] else 0
    vault_net = vault_deposit + vault_withdraw
    
    # --- 3. Calculate Closing Balance ---
    # Liquid Net Flow = Income + Expense - Vault_Net
    
    liquid_net_flow = inc_exp_map[CategoryType.INCOME] + inc_exp_map[CategoryType.EXPENSE] - vault_net
    liquid_closing = liquid_opening_val + liquid_net_flow
    
    vault_closing = vault_opening_val + vault_net
    
    return {
        "period": {"start": start_date, "end": end_date},
        "liquid": {
            "opening": liquid_opening_val,
            "income": inc_exp_map[CategoryType.INCOME],
            "expense": inc_exp_map[CategoryType.EXPENSE],
            "net_flow": liquid_net_flow,
            "closing": liquid_closing
        },
        "vault": {
            "opening": vault_opening_val,
            "deposit": vault_deposit,
            "withdraw": vault_withdraw,
            "closing": vault_closing
        }
    }
