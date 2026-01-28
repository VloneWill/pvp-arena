from typing import Dict

from fastapi.testclient import TestClient


def auth_headers(client: TestClient, username: str, password: str = "password123", class_name: str = "warrior") -> Dict[str, str]:
    # Register (ignore if already exists, but in-memory DB will be fresh per test)
    client.post("/auth/register", json={"username": username, "password": password, "class_name": class_name})

    # Login for token
    r = client.post("/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200
    token = r.json()["access_token"]

    return {"Authorization": f"Bearer {token}"}


def my_user_id(client: TestClient, headers: Dict[str, str]) -> int:
    r = client.get("/auth/me", headers=headers)
    assert r.status_code == 200
    return r.json()["id"]

