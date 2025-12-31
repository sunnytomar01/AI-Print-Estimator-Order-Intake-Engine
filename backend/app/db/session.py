from sqlmodel import create_engine, Session
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@db:5432/ai_print")

def get_engine():
    return create_engine(DATABASE_URL, echo=True)


def get_session() -> Session:
    engine = get_engine()
    return Session(engine)
