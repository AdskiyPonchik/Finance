from datetime import date, timedelta

import pytest
from sqlmodel import select

from app.api.utils import due_dates, process_recurring_transactions
from app.core.auth import create_access_token
from app.core.models import Category, CategoryType, RecurringTransaction, Transaction, User


def category(client, auth, kind="expense", name="Food"):
    response = client.post("/api/categories/", headers=auth, json={
        "name": name, "type": kind, "color": "#123456",
    })
    assert response.status_code == 201, response.text
    return response.json()["id"]


def post_transaction(client, auth, category_id, amount, day="2026-01-15"):
    return client.post("/api/transactions/", headers=auth, json={
        "title": "Test", "amount": amount, "date": day, "category_id": category_id,
    })


def test_health_and_frontend(client):
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/health/ready").status_code == 200
    assert client.get("/").status_code == 200
    assert client.get("/static/js/app.js").status_code == 200


def test_login_and_identity(client, user, auth):
    assert client.get("/api/users/me", headers=auth).json() == {"id": user.id, "username": "alice"}
    assert client.get("/api/users/me").status_code == 401
    for username in ("alice", "missing"):
        assert client.post("/api/token", data={"username": username, "password": "wrong"}).status_code == 401
    expired = create_access_token({"sub": "alice"}, timedelta(seconds=-1))
    assert client.get("/api/users/me", headers={"Authorization": f"Bearer {expired}"}).status_code == 401
    assert client.get("/api/users/me", headers={"Authorization": "Bearer invalid"}).status_code == 401


@pytest.mark.parametrize("amount", [0, 12, 1.5, "-100", True, -(2**53)])
def test_invalid_expense_amounts(client, auth, amount):
    cat_id = category(client, auth)
    assert post_transaction(client, auth, cat_id, amount).status_code == 422
    assert client.get("/api/transactions/", headers=auth).json()["total"] == 0


def test_transaction_lifecycle_and_pagination(client, auth):
    cat_id = category(client, auth)
    first = post_transaction(client, auth, cat_id, -1200)
    assert first.status_code == 200
    tx_id = first.json()["id"]
    second = post_transaction(client, auth, cat_id, -500)
    assert second.status_code == 200
    page = client.get("/api/transactions/?limit=1&offset=0", headers=auth).json()
    assert page["total"] == 2
    assert [item["id"] for item in page["items"]] == [second.json()["id"]]
    page2 = client.get("/api/transactions/?limit=1&offset=1", headers=auth).json()
    assert [item["id"] for item in page2["items"]] == [tx_id]
    response = client.put(f"/api/transactions/{tx_id}", headers=auth, json={
        "title": "Updated", "amount": -1500, "date": "2026-02-01", "category_id": cat_id,
    })
    assert response.status_code == 200
    assert response.json()["amount"] == -1500
    assert response.json()["date"] == "2026-02-01"
    assert client.delete(f"/api/categories/{cat_id}", headers=auth).status_code == 409
    assert client.delete(f"/api/transactions/{tx_id}", headers=auth).status_code == 204
    assert client.get("/api/transactions/", headers=auth).json()["total"] == 1


def test_duplicate_category(client, auth):
    category(client, auth)
    response = client.post("/api/categories/", headers=auth, json={
        "name": "Food", "type": "expense", "color": "#123456",
    })
    assert response.status_code == 409


def test_other_users_cannot_access_data(client, auth, session, password_hash):
    cat_id = category(client, auth)
    tx_id = post_transaction(client, auth, cat_id, -500).json()["id"]
    session.add(User(username="bob", hashed_password=password_hash))
    session.commit()
    bob = {"Authorization": f"Bearer {create_access_token({'sub': 'bob'})}"}
    assert client.get("/api/categories/", headers=bob).json() == []
    assert client.get("/api/transactions/", headers=bob).json() == {"total": 0, "items": []}
    assert client.get("/api/balance/", headers=bob).json() == {"liquid": 0, "vault": 0, "net_worth": 0}
    assert post_transaction(client, bob, cat_id, -100).status_code == 404
    assert client.delete(f"/api/transactions/{tx_id}", headers=bob).status_code == 404
    assert client.put(f"/api/transactions/{tx_id}", headers=bob, json={
        "amount": -100, "date": "2026-01-15", "category_id": cat_id,
    }).status_code == 404
    assert client.delete(f"/api/categories/{cat_id}", headers=bob).status_code == 404


def test_balance_and_cashflow(client, auth):
    income = category(client, auth, "income", "Salary")
    expense = category(client, auth)
    vault = category(client, auth, "vault", "Savings")
    for cat_id, amount, day in [
        (income, 10000, "2025-12-31"), (income, 100000, "2026-01-01"),
        (expense, -20000, "2026-01-15"), (vault, -30000, "2026-01-31"),
        (vault, 5000, "2026-01-31"), (expense, -1000, "2026-02-01"),
    ]:
        assert post_transaction(client, auth, cat_id, amount, day).status_code == 200
    assert client.get("/api/balance/", headers=auth).json() == {
        "liquid": 64000, "vault": 25000, "net_worth": 89000,
    }
    response = client.get("/api/analytics/cashflow?start_date=2026-01-01&end_date=2026-01-31", headers=auth)
    assert response.status_code == 200
    assert response.json()["liquid"] == {
        "opening": 10000, "income": 100000, "expense": -20000, "net_flow": 55000, "closing": 65000,
    }
    assert response.json()["vault"] == {"opening": 0, "deposit": 30000, "withdraw": -5000, "closing": 25000}
    assert client.get("/api/analytics/expenses", headers=auth).json()[0]["total"] == 21000
    assert client.get("/api/analytics/heatmap", headers=auth).json()["2026-01-31"] == 2
    assert client.get("/api/analytics/cashflow?start_date=2026-02-01&end_date=2026-01-01", headers=auth).status_code == 422


def test_recurring_catchup_is_idempotent_even_after_transaction_deletion(session, user):
    cat = Category(name="Subscription", type=CategoryType.EXPENSE, owner_id=user.id)
    session.add(cat)
    session.flush()
    recurring = RecurringTransaction(
        title="Monthly", amount=-999, category_id=cat.id, type="expense", day_of_month=31,
        created_on=date(2024, 1, 31), owner_id=user.id,
    )
    session.add(recurring)
    session.commit()
    assert process_recurring_transactions(session, user.id, date(2024, 3, 31)) == 3
    session.commit()
    rows = session.exec(select(Transaction).order_by(Transaction.date)).all()
    assert [row.date.date() for row in rows] == [date(2024, 1, 31), date(2024, 2, 29), date(2024, 3, 31)]
    session.delete(rows[0])
    # Force a historical rescan to verify the durable receipt prevents duplicates.
    recurring.last_run_date = None
    session.add(recurring)
    session.commit()
    assert process_recurring_transactions(session, user.id, date(2024, 3, 31)) == 0
    session.commit()
    assert len(session.exec(select(Transaction)).all()) == 2


def test_recurring_api(client, auth):
    cat_id = category(client, auth)
    payload = {"title": "Rent", "amount": -1000, "category_id": cat_id, "type": "expense", "day_of_month": 1}
    assert client.post("/api/recurring/", headers=auth, json={**payload, "type": "income"}).status_code == 422
    assert client.post("/api/recurring/", headers=auth, json={**payload, "day_of_month": 32}).status_code == 422
    response = client.post("/api/recurring/", headers=auth, json=payload)
    assert response.status_code == 201
    assert len(client.get("/api/recurring/", headers=auth).json()) == 1
    assert client.delete(f"/api/categories/{cat_id}", headers=auth).status_code == 409
    assert client.post("/api/recurring/process", headers=auth).status_code == 200
    assert client.post("/api/recurring/process", headers=auth).json() == {"created": 0}
    assert client.delete(f"/api/recurring/{response.json()['id']}", headers=auth).status_code == 204


def test_due_dates_skip_before_creation_and_cross_year():
    item = RecurringTransaction(day_of_month=1, created_on=date(2025, 12, 15))
    assert list(due_dates(item, date(2026, 2, 1))) == [date(2026, 1, 1), date(2026, 2, 1)]
