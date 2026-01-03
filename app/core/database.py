from sqlmodel import SQLModel, create_engine, Session
from fastapi import Depends
from typing import Generator

#sqlite_url = "sqlite:///./database.db"
DATABASE_URL = "postgresql://admin:password@localhost:5432/finbrew"
engine = create_engine(DATABASE_URL, echo=False)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session() -> Generator:
    with Session(engine) as session:
        yield session