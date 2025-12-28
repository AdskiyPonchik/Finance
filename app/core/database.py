from sqlmodel import SQLModel, create_engine, Session
from fastapi import Depends
from typing import Generator

sqlite_url = "sqlite:///./database.db"
engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session() -> Generator:
    with Session(engine) as session:
        yield session