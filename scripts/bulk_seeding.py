import time
import random
from datetime import datetime, timedelta
from sqlalchemy import text
from sqlmodel import Session, create_engine, select
from app.core.models import Transaction, Category, User

# Database connection string for PostgreSQL
DATABASE_URL = "postgresql://admin:password@localhost:5432/finbrew"
engine = create_engine(DATABASE_URL)


def bulk_seed(total_records=1_000_000, batch_size=50_000):
    """
    Directly seeds the PostgreSQL database with a large number of transactions.
    Bypasses the API for maximum performance.
    """

    print("(!) Clearing old data...")
    with Session(engine) as session:
        session.exec(text("TRUNCATE TABLE transaction RESTART IDENTITY CASCADE;"))
        session.commit()

    start_time = time.time()

    # 1. Setup: Fetch admin user and available categories
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == "admin")).first()
        categories = session.exec(select(Category).where(Category.owner_id == user.id)).all()

        if not user or not categories:
            print("(!) Error: Ensure 'admin' user and categories exist in the DB.")
            return

        cat_ids = [c.id for c in categories]
        admin_id = user.id

    print(f"(!) Starting bulk injection of {total_records} records into Postgres...")

    # 2. Main seeding loop
    for i in range(0, total_records, batch_size):
        batch_start = time.time()

        with Session(engine) as session:
            transactions = []
            for _ in range(batch_size):
                # Generate random date within the last year
                days_back = random.randint(0, 365)
                tx_date = datetime.now() - timedelta(days=days_back)

                # Financial logic: 51% income, 49% expenses
                is_income = random.random() < 0.51
                # Amount in cents (randomized between 5 and 5000 units)
                amount = random.randint(5, 5000) * (100 if is_income else -100)

                # Instantiate Transaction model
                tx = Transaction(
                    title=f"Bulk Seed Tx {i}",
                    amount=amount,
                    date=tx_date,
                    owner_id=admin_id,
                    category_id=random.choice(cat_ids)
                )
                transactions.append(tx)

            # Use bulk_save_objects for high-performance insertion
            session.bulk_save_objects(transactions)
            session.commit()

        batch_end = time.time()
        print(f" -> Processed {i + batch_size} | Batch time: {batch_end - batch_start:.2f}s")

    total_time = time.time() - start_time
    print(f"\n(!!) SUCCESS: 1,000,000 records seeded in {total_time:.2f} seconds.")
    print(f"Average throughput: {total_records / total_time:.0f} tx/sec.")


if __name__ == "__main__":
    bulk_seed()