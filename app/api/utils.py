from datetime import date, datetime
from sqlmodel import Session, select
from app.core.models import RecurringTransaction, Transaction

def process_recurring_transactions(session: Session, user_id: int):
    today = date.today()
    
    # Fetch all active recurring transactions for the user
    statement = select(RecurringTransaction).where(
        RecurringTransaction.owner_id == user_id,
        RecurringTransaction.is_active == True
    )
    recurring_transactions = session.exec(statement).all()
    
    for item in recurring_transactions:
        # Check if today is past or equal to the scheduled day
        if today.day >= item.day_of_month:
            # Check if it hasn't run this month
            if item.last_run_date is None or item.last_run_date.month < today.month or item.last_run_date.year < today.year:
                # Create a new Transaction
                new_transaction = Transaction(
                    title=item.title,
                    amount=item.amount,
                    date=datetime.combine(today, datetime.min.time()), # Use today's date
                    owner_id=user_id,
                    category_id=item.category_id
                )
                session.add(new_transaction)
                
                # Update last_run_date
                item.last_run_date = today
                session.add(item)
    
    session.commit()
