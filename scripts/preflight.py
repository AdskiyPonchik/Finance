from sqlalchemy import inspect, text

from app.core.database import engine


def main():
    required = {"user", "category", "transaction", "recurringtransaction"}
    with engine.connect() as connection:
        present = set(inspect(connection).get_table_names())
        if not required <= present:
            raise SystemExit("Legacy tables not found. Use 'alembic upgrade head' for a new empty DB.")
        queries = {
            "invalid transactions": """
                SELECT t.id FROM transaction t JOIN category c ON c.id = t.category_id
                WHERE t.amount = 0 OR t.owner_id <> c.owner_id
                OR (CAST(c.type AS TEXT) = 'INCOME' AND t.amount < 0)
                OR (CAST(c.type AS TEXT) = 'EXPENSE' AND t.amount > 0)
            """,
            "invalid subscriptions": """
                SELECT r.id FROM recurringtransaction r JOIN category c ON c.id = r.category_id
                WHERE r.amount = 0 OR r.day_of_month NOT BETWEEN 1 AND 31
                OR r.type NOT IN ('income', 'expense') OR r.owner_id <> c.owner_id
                OR UPPER(r.type) <> CAST(c.type AS TEXT)
                OR (r.type = 'income' AND r.amount < 0)
                OR (r.type = 'expense' AND r.amount > 0)
            """,
        }
        failed = False
        for label, query in queries.items():
            rows = connection.execute(text(query)).scalars().all()
            if rows:
                failed = True
                print(f"{label}: {len(rows)}; first IDs: {rows[:20]}")
        if failed:
            raise SystemExit("Fix the listed legacy records explicitly before migrating. No data was changed.")
    print("Legacy data checks passed. Verify the schema matches baseline before 'alembic stamp 0001'.")


if __name__ == "__main__":
    main()