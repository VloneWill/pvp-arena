#imports for the database
import os
from sqlalchemy import create_engine

#imports for the sessionmaker
from sqlalchemy.orm import sessionmaker, declarative_base

#create the database url (env-driven, sqlite fallback)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./pvp_arena.db")

#sqlite needs special connect args, postgres does not
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

#create the engine
engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
)

#create the session local
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

#create the base
Base = declarative_base()

#create the get db function
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
