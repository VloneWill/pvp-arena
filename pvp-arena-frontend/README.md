# PvP Arena Frontend

Minimal React + Vite frontend for the PvP Arena game.

## Setup

1. Install dependencies:
```bash
npm install
```

2. Start the development server:
```bash
npm run dev
```

The frontend will run on `http://localhost:5173`.

## Backend Setup

Make sure the backend is running on `http://127.0.0.1:8000`:

```bash
# From the backend directory
uvicorn app.main:app --reload
```

## Usage

1. **Register/Login**: Create an account or login with existing credentials
2. **Join Matchmaking**: Click "Join Matchmaking" to enter the queue
3. **Wait for Match**: The UI will auto-refresh until you're matched with another player
4. **Play**: Once matched, use Attack/Defend/Heal buttons on your turn
5. **Auto-refresh**: Game state refreshes every 1 second automatically

## Testing with Two Players

Open two browser windows (or use incognito mode) and login as different users to test the full matchmaking and combat flow.
