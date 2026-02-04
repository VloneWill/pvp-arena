# PvP Arena Backend

A turn-based PvP arena backend built with FastAPI, featuring JWT authentication,
matchmaking, and a fully isolated combat engine with comprehensive test coverage.

This project is designed to showcase clean backend architecture, domain-driven
game logic, and testable systems rather than frontend or UI concerns.

Status: Actively under development.

---

## Architecture Overview

This project is a FastAPI-based PvP arena backend organized into three primary layers.

### API Layer (app/api/)
- FastAPI routers for authentication, matchmaking, and matches
- Endpoints are intentionally thin and delegate all game logic to the domain layer
- Responsible only for request validation, authentication, and HTTP responses

### Domain / Engine Layer (app/game/)
Pure Python game logic with no FastAPI or database coupling:
- engine.py: In-memory MatchmakingQueue used to pair players into matches
- combat.py: Low-level combat primitives and the high-level CombatEngine that
  enforces turn order, match state, and action validity

### Persistence Layer (app/db/)
- SQLAlchemy models and database session management
- Stores User and Match records
- Cleanly separated from both HTTP and combat logic

This separation keeps HTTP concerns (serialization, authentication, status codes)
out of the core game rules and allows the game logic to evolve independently of
the API layer.

---

## Why the Combat Engine Is Isolated

The CombatEngine in app/game/combat.py is designed to be:

- Deterministic and side-effect free (aside from mutating Match state)
  It operates purely on domain entities and controlled randomness, with no
  knowledge of FastAPI, HTTP, or database session lifecycles.

- The single source of truth for rules
  Turn enforcement, invalid actions (wrong player, dead player), and
  no actions after match completion are all centralized in one place.
  The API layer simply catches domain errors and translates them into HTTP responses.

- Easy to test
  Unit tests exercise the engine directly without going through HTTP,
  ensuring that game rules remain correct even as API routes evolve.

This approach avoids duplicated rule logic across endpoints and reduces the risk
of the API and the game rules drifting apart over time.

---

## Testing Strategy

The project uses a layered testing approach to ensure correctness at both the
game-rule level and the API integration level.

### Combat Engine Tests (app/tests/test_combat.py)
- Validate attacks, defense, healing, and health bounds
- Enforce turn switching and action order
- Ensure players cannot act when it is not their turn, when dead, or after a match ends
- Test the CombatEngine and low-level combat functions directly

### Matchmaking Queue Tests (app/tests/test_queue.py)
- Verify join and leave behavior
- Prevent duplicate queue entries
- Ensure FIFO pairing logic
- Validate queue state after operations

### End-to-End API Flow Tests (app/tests/test_api_flow.py)
- Use FastAPI TestClient with an in-memory SQLite database
- Override dependencies via conftest.py
- Exercise full flows:
  - /auth/register
  - /auth/login
  - /matchmaking/join
  - /matches/{id}/action
  - /matches/{id}/state
- Use controlled randomness via monkeypatch to make combat deterministic

---

## Backend commands require venv

All backend commands (running the server, migrations, tests) must be run with the project virtual environment activated. From the repo root:

```bash
source .venv/bin/activate
```

Then run `python -m ...`, `alembic ...`, `uvicorn ...`, or `pytest ...` as needed. The sections below assume the venv is active.

---

## Configuration

This project uses environment variables for configuration via pydantic-settings.

Create a .env file from the example:

    cp .env.example .env

### Username Moderation
Usernames are validated server-side to prevent abusive or offensive language.  
Registrations that violate these rules are rejected with a generic error message.

### Required variables

- JWT_SECRET – secret key used to sign JWTs
- DATABASE_URL – database connection string

Example for Supabase Postgres:

    DATABASE_URL=postgresql+psycopg2://USER:PASSWORD@HOST:5432/DBNAME

The application will default to a local SQLite database if DATABASE_URL is not set.

### Running the server

    source .venv/bin/activate
    uvicorn app.main:app --reload

### Environment variables and production redeploy

**Production redeploy is required to pick up any change to environment variables.**

- **Backend (e.g. Render):** After changing `DATABASE_URL`, `JWT_SECRET`, or other env vars in the dashboard, redeploy the service so the new values are applied.
- **Frontend (e.g. Vercel):** After changing build or runtime env vars, redeploy so the app uses the updated configuration.

---

## Database migrations (Alembic)

**Schema evolution is done via Alembic. Do not rely on `Base.metadata.create_all()` for production updates** — it does not perform migrations (renames, type changes, drops).

### Local development

1. Create/activate the virtual environment and install dependencies:
   ```bash
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Apply migrations to bring the database up to date:
   ```bash
   alembic upgrade head
   ```
3. Optional local bootstrap (drops and recreates all tables; **do not use in production**):
   ```bash
   python reset_db.py
   ```
   Then run `alembic upgrade head` if you want a clean schema again.
4. **If the database already has tables** (e.g. from an older `create_all` or `reset_db.py` run) and you have no `alembic_version` table, stamp the initial revision then upgrade to add only new columns:
   ```bash
   alembic stamp 15bed9213a5d
   alembic upgrade head
   ```

### Production (e.g. Render)

- Run migrations as part of deploy/startup, or as a one-off before starting the app:
  ```bash
  alembic upgrade head
  ```
- Ensure `DATABASE_URL` is set in the environment so Alembic uses the same database as the app.

### Creating a new migration

After changing `app.db.models`:

```bash
source .venv/bin/activate
alembic revision --autogenerate -m "description of change"
alembic upgrade head
```

---

## Running Tests

    source .venv/bin/activate
    pytest -v

Optional coverage:

    pytest --cov=app --cov-report=term-missing

---

## Running Locally

    source .venv/bin/activate
    pip install -r requirements.txt
    uvicorn app.main:app --reload

The API will be available at:
http://127.0.0.1:8000/docs

---

## Future Work

- Persistent matchmaking queues
- Additional classes and abilities
