"""Create the documented local demo account without changing existing users."""

from sqlmodel import Session, select

from app.cli import DEMO_PASSWORD, DEMO_USERNAME, create_user_record
from app.core.auth import verify_password
from app.core.database import engine
from app.core.models import User


def main() -> None:
    with Session(engine) as session:
        existing = session.exec(select(User).where(User.username == DEMO_USERNAME)).first()
        if existing is not None:
            if not verify_password(DEMO_PASSWORD, existing.hashed_password):
                raise SystemExit(
                    "User 'alice' already exists with a different password; it was not changed."
                )
            print("Demo user 'alice' already exists; nothing changed.")
            return
        create_user_record(session, DEMO_USERNAME, DEMO_PASSWORD)
    print("Demo user 'alice' created with the documented demo password.")


if __name__ == "__main__":
    main()
