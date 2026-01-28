#imports for the dotenv
from dotenv import load_dotenv
load_dotenv()

#imports for the database
from app.db.database import Base, engine

#imports for the models
import app.db.models  # ensures models are registered

def reset_database():
    print("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)

    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)

    print("Database reset complete")

if __name__ == "__main__":
    reset_database()
