#imports for the database
from sqlalchemy import create_engine

#imports for the sessionmaker
from sqlalchemy.orm import sessionmaker, declarative_base

#create the database url
SQLALCHEMY_DATABASE_URL = "sqlite:///./pvp_arena.db"

#create the engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
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
