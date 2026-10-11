import argparse
from getpass import getpass

from sqlmodel import Session, select

from app.api.utils import process_recurring_transactions
from app.core.auth import get_password_hash
from app.core.database import engine
from app.core.models import Category, CategoryType, RecurringTransaction, User


def create_user(username: str):
    username = username.strip()
    if not 1 <= len(username) <= 64:
        raise SystemExit("Username must contain 1–64 characters.")
    password = getpass("Password (at least 12 characters): ")
    if len(password) < 12 or len(password.encode("utf-8")) > 72:
        raise SystemExit("Password must be at least 12 characters and at most 72 UTF-8 bytes.")
    if password != getpass("Repeat password: "):
        raise SystemExit("Passwords do not match.")
    with Session(engine) as session:
        if session.exec(select(User).where(User.username == username)).first() is not None:
            raise SystemExit("User already exists.")
        user = User(username=username, hashed_password=get_password_hash(password))
        session.add(user)
        session.flush()
        for name, kind, color in [
            ("Groceries", CategoryType.EXPENSE, "#4CAF50"),
            ("Rent", CategoryType.EXPENSE, "#F44336"),
            ("Salary", CategoryType.INCOME, "#FFC107"),
            ("Savings", CategoryType.VAULT, "#795548"),
        ]:
            session.add(Category(name=name, type=kind, color=color, owner_id=user.id))
        session.commit()
    print(f"User {username!r} created.")


def set_password(username: str):
    password = getpass("New password (at least 12 characters): ")
    if len(password) < 12 or len(password.encode("utf-8")) > 72:
        raise SystemExit("Password must be at least 12 characters and at most 72 UTF-8 bytes.")
    if password != getpass("Repeat password: "):
        raise SystemExit("Passwords do not match.")
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == username)).first()
        if user is None:
            raise SystemExit("User not found.")
        user.hashed_password = get_password_hash(password)
        session.add(user)
        session.commit()
    print("Password updated. Rotate SECRET_KEY too if existing tokens must be revoked.")


def process_all():
    with Session(engine) as session:
        owner_ids = session.exec(select(RecurringTransaction.owner_id).distinct()).all()
    total = 0
    for owner_id in owner_ids:
        with Session(engine) as session:
            total += process_recurring_transactions(session, owner_id)
            session.commit()
    print(f"Created {total} transactions.")


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("create-user").add_argument("username")
    commands.add_parser("set-password").add_argument("username")
    commands.add_parser("process-recurring")
    args = parser.parse_args()
    if args.command == "create-user":
        create_user(args.username)
    elif args.command == "set-password":
        set_password(args.username)
    else:
        process_all()


if __name__ == "__main__":
    main()