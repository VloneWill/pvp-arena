from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.db import models
from app.db.database import engine

app = FastAPI(title="PvP Arena")

models.Base.metadata.create_all(bind=engine)

app.include_router(auth_router)

@app.get("/health")
def health():
    return {"status": "ok"}
