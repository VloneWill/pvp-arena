"""Matchmaking leave: join/leave, idempotent leave, leave prevents match."""
from app.tests.helpers import auth_headers


class TestMatchmakingLeave:
    def test_join_then_leave_removes_from_queue(self, client):
        h = auth_headers(client, "user1")
        r1 = client.post("/matchmaking/join", headers=h)
        assert r1.status_code == 200
        assert r1.json()["status"] == "waiting"
        r2 = client.post("/matchmaking/leave", headers=h)
        assert r2.status_code == 200
        assert r2.json()["status"] == "left"
        status = client.get("/matchmaking/status", headers=h).json()
        assert status["in_queue"] is False
        assert status["position"] is None

    def test_double_leave_ok(self, client):
        """Leaving when not in queue is idempotent and safe."""
        h = auth_headers(client, "user1")
        client.post("/matchmaking/leave", headers=h)
        r = client.post("/matchmaking/leave", headers=h)
        assert r.status_code == 200
        assert r.json()["status"] == "left"

    def test_leaving_prevents_match_creation(self, client):
        """Waiter joins; leaver never joins (or leaves before joining). Third joins and matches with waiter only."""
        h1 = auth_headers(client, "waiter")
        h2 = auth_headers(client, "leaver")
        h3 = auth_headers(client, "third")
        client.post("/matchmaking/join", headers=h1)
        client.post("/matchmaking/leave", headers=h2)
        r = client.post("/matchmaking/join", headers=h3)
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "matched"
        match = body["match"]
        ids = [match["player1_id"], match["player2_id"]]
        waiter_id = client.get("/auth/me", headers=h1).json()["id"]
        third_id = client.get("/auth/me", headers=h3).json()["id"]
        leaver_id = client.get("/auth/me", headers=h2).json()["id"]
        assert waiter_id in ids
        assert third_id in ids
        assert leaver_id not in ids
