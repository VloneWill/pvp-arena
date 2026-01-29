#imports for the dotenv
from dotenv import load_dotenv
load_dotenv()

#imports for the FastAPI app
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

#imports for the routers
from app.api.auth import router as auth_router
from app.api.matchmaking import router as matchmaking_router
from app.api.matches import router as matches_router  

#imports for the database
from app.db import models
from app.db.database import engine

#create the FastAPI app
app = FastAPI(title="PvP Arena")

#add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#create the database tables
models.Base.metadata.create_all(bind=engine)

#include the routers
app.include_router(auth_router)
app.include_router(matchmaking_router)
app.include_router(matches_router)

#create the health check endpoint
@app.get("/health")
def health():
    return {"status": "ok"}
