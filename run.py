import sys
from getpass import getpass

import uvicorn
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select

from app.cli import DEMO_PASSWORD, DEMO_USERNAME, create_user_record
from app.core.database import engine
from app.core.models import User


def database_has_users() -> bool:
    with Session(engine) as session:
        return session.exec(select(User.id).limit(1)).first() is not None


def ask_yes_no(question: str) -> bool:
    while True:
        answer = input(f"{question} [y/n]: ").strip().lower()
        if answer in {"y", "yes"}:
            return True
        if answer in {"n", "no"}:
            return False
        print("Please answer y or n.")


def setup_initial_user() -> None:
    try:
        if database_has_users():
            return
    except SQLAlchemyError as exc:
        raise SystemExit(
            "Database is not ready. Start PostgreSQL and run "
            "`python -m alembic upgrade head` before starting the app."
        ) from exc

    if not sys.stdin.isatty():
        raise SystemExit(
            "No application user exists. Run `python -m app.cli create-user <username>` "
            "from an interactive terminal."
        )

    print("No application user exists yet.")
    if ask_yes_no(f"Create the demo account {DEMO_USERNAME!r}?"):
        username = DEMO_USERNAME
        password = DEMO_PASSWORD
    else:
        username = input("Username: ").strip()
        password = getpass("Password (at least 12 characters): ")
        if password != getpass("Repeat password: "):
            raise SystemExit("Passwords do not match.")

    try:
        with Session(engine) as session:
            create_user_record(session, username, password)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    print(f"User {username!r} created.")


if __name__ == "__main__":
    setup_initial_user()
    uvicorn.run("app.main:app",
                host="127.0.0.1",
                port=8080,
                reload=True)
