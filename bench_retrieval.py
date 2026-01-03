import time
import random
from datetime import datetime, timedelta
from sqlmodel import Session, create_engine, select, func
from app.core.models import Transaction, Category, User

# Database connection string for PostgreSQL
DATABASE_URL = "postgresql://admin:password@localhost:5432/finbrew"
engine = create_engine(DATABASE_URL)

def run_benchmarks(iterations=100):
    """
    Directly seeds the PostgreSQL database with a large number of transactions.
    Bypasses the API for maximum performance.
    :param iterations:
    :return:
    """
    print(f"Running benchmarks ({iterations} iterations each)...")
    with Session(engine) as session:
        # Get min and max IDs for random selection
        ids = session.exec(select(func.min(Transaction.id), func.max(Transaction.id))).first()
        min_id, max_id = ids[0], ids[1]

        # --- TEST 1: Point Lookup (Random ID) ---
        start = time.time()
        for _ in range(iterations):
            random_id = random.randint(min_id, max_id)
            session.exec(select(Transaction).where(Transaction.id == random_id)).first()
        p_time = (time.time() - start) / iterations
        print(f" -> Point Lookup (by ID): {p_time * 1000:.3f} ms / query")

        # --- TEST 2: Range Scan (1 Week of Data) ---
        start = time.time()
        for _ in range(iterations):
            # Random date within the last year
            days_back = random.randint(7, 350)
            end_date = datetime.now() - timedelta(days=days_back)
            start_date = end_date - timedelta(days=7)

            session.exec(
                select(Transaction).where(Transaction.date >= start_date, Transaction.date <= end_date).limit(100)
            ).all()
        r_time = (time.time() - start) / iterations
        print(f" -> Range Scan (7 days, limit 100): {r_time * 1000:.3f} ms / query")

        # --- TEST 3: Full Aggregation (Heatmap Logic) ---
        # This scans the whole table or a large index!
        start = time.time()
        for _ in range(iterations // 10):  # Doing fewer iterations as it's heavy
            statement = (
                select(func.date(Transaction.date), func.sum(func.abs(Transaction.amount)))
                .group_by(func.date(Transaction.date))
            )
            session.exec(statement).all()
        a_time = (time.time() - start) / (iterations // 10)
        print(f" -> Heatmap Aggregation (Full Table): {a_time * 1000:.3f} ms / query")

if __name__ == "__main__":
    run_benchmarks()