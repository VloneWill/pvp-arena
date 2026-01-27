## Architecture overview

This project is a small FastAPI-based PvP arena backend with three main layers:

- **API layer (`app/api/`)**: FastAPI routers for auth, matchmaking, and matches. These endpoints are intentionally thin and delegate all game logic to the combat and queue engines.
- **Domain / engine layer (`app/game/`)**: Pure Python game logic:
  - `engine.py` contains the in-memory `MatchmakingQueue` used to pair players into matches.
  - `combat.py` contains the low-level combat primitives and the high-level `CombatEngine` that enforces turn order, match state, and action validity.
- **Persistence layer (`app/db/`)**: SQLAlchemy models and database session management for `User` and `Match` records.

This separation keeps HTTP concerns (serialization, auth, status codes) out of the core game rules and makes it easy to evolve the game independently of the transport.

## Why the combat engine is isolated

The `CombatEngine` in `app/game/combat.py` is designed to be:

- **Deterministic and side-effect free (aside from mutating `Match`)**: It works purely in terms of `Match` entities and random damage rolls, with no knowledge of FastAPI, HTTP, or the database session lifecycle.
- **The single source of truth for rules**: Turn enforcement, “dead players cannot act”, “wrong player cannot act”, and “no actions after a finished match” all live in one place. The API layer simply catches `InvalidActionError` / `MatchNotActiveError` and translates them into HTTP errors.
- **Easy to test**: Unit tests in `app/tests/test_combat.py` exercise the engine directly without going through HTTP, so rules remain well-specified even if the API routes change.

By isolating the engine, you avoid duplicated rule logic in multiple endpoints and reduce the chance that the API and the game rules drift apart over time.

## Testing strategy

The test suite covers three layers:

- **Unit tests for combat logic** (`app/tests/test_combat.py`):
  - Validate attacks, defense, healing, health bounds, double-attack behavior, turn switching, and “cannot act when match is over / not your turn / dead”.
  - Use the low-level functions and `CombatEngine` directly.
- **Unit tests for matchmaking queue** (`app/tests/test_queue.py`):
  - Verify join/leave behavior, no duplicates, FIFO pairing, and queue order after operations.
- **End-to-end API tests** (`app/tests/test_api_flow.py`):
  - Use `TestClient` with an in-memory SQLite DB (via `conftest.py` and overridden `get_db`).
  - Exercise `/auth/register`, `/auth/login`, `/matchmaking/join`, `/matches/{id}/action`, and `/matches/{id}/state` with real auth headers and controlled randomness using `monkeypatch`.

To run the tests locally:

```bash
pytest -v
```

### Test coverage

If you enable `pytest-cov`, you can run:

```bash
pytest --cov=app --cov-report=term-missing
```

And add a badge like this to the top of the README (replace the URL with your actual CI/coverage provider):

```markdown
![coverage](https://img.shields.io/badge/coverage-XX%25-brightgreen)
```

