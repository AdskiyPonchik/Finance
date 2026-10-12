import builtins

import pytest
from sqlmodel import select

import run
from app.cli import create_user_record
from app.core.auth import verify_password
from app.core.models import Category, User


def test_create_user_record_creates_user_and_starter_categories(session):
    user = create_user_record(session, "  charlie  ", "charlie-password")

    assert user.username == "charlie"
    assert verify_password("charlie-password", user.hashed_password)
    categories = session.exec(select(Category).where(Category.owner_id == user.id)).all()
    assert {(category.name, category.type.value) for category in categories} == {
        ("Groceries", "expense"),
        ("Rent", "expense"),
        ("Salary", "income"),
        ("Savings", "vault"),
    }


def test_create_user_record_rejects_duplicate_username(session, password_hash):
    session.add(User(username="charlie", hashed_password=password_hash))
    session.commit()

    with pytest.raises(ValueError, match="User already exists"):
        create_user_record(session, "charlie", "charlie-password")


def test_create_user_record_validates_credentials(session):
    for username, password, message in [
        ("", "long-enough-password", "Username must contain 1–64 characters."),
        ("charlie", "too-short", "Password must be at least 12 characters"),
    ]:
        with pytest.raises(ValueError, match=message):
            create_user_record(session, username, password)


def test_ask_yes_no_reprompts_until_answer(monkeypatch, capsys):
    answers = iter(["maybe", "YES"])
    monkeypatch.setattr(builtins, "input", lambda _: next(answers))

    assert run.ask_yes_no("Create demo?") is True
    assert "Please answer y or n." in capsys.readouterr().out


def test_setup_initial_user_does_nothing_when_user_exists(monkeypatch):
    monkeypatch.setattr(run, "database_has_users", lambda: True)
    monkeypatch.setattr(
        builtins,
        "input",
        lambda _: pytest.fail("Existing installations must not show the onboarding prompt"),
    )

    run.setup_initial_user()
