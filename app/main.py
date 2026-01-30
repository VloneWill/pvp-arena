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
from app.api.leaderboard import router as leaderboard_router

#create the FastAPI app
app = FastAPI(title="PvP Arena")

#add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://pvp-arena.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Schema is managed by Alembic. For local dev bootstrap use: alembic upgrade head
# or reset_db.py. Do NOT rely on create_all for production schema evolution.

#include the routers
app.include_router(auth_router)
app.include_router(matchmaking_router)
app.include_router(matches_router)
app.include_router(leaderboard_router)

#create the health check endpoint
@app.get("/health")
def health():
    return {"status": "ok"}
