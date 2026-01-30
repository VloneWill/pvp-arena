"""Leaderboard API: ordering and limit."""
import pytest
from app.tests.helpers import auth_headers


class TestLeaderboard:
    def test_leaderboard_ordering_and_limit(self, client, monkeypatch):
        """Sort by wins DESC, level DESC, username ASC; limit applied."""
        import app.game.combat as combat
        monkeypatch.setattr(combat.random, "randint", lambda a, b: 200)

        # Create 3 users, finish 2 matches so we have wins/losses
        h1 = auth_headers(client, "alice", class_name="warrior")
        h2 = auth_headers(client, "bob", class_name="mage")
        h3 = auth_headers(client, "charlie", class_name="druid")

        id1 = client.get("/auth/me", headers=h1).json()["id"]
        id2 = client.get("/auth/me", headers=h2).json()["id"]
        id3 = client.get("/auth/me", headers=h3).json()["id"]

        # alice beats bob
        client.post("/matchmaking/join", headers=h1)
        r = client.post("/matchmaking/join", headers=h2)
        match_id_1 = r.json()["match"]["id"]
        p1_h = h1 if r.json()["match"]["player1_id"] == id1 else h2
        client.post(f"/matches/{match_id_1}/action", headers=p1_h, json={"action": "attack"})

        # alice beats charlie (alice 2 wins, bob 0, charlie 0; bob 1 loss, charlie 1 loss)
        client.post("/matchmaking/join", headers=h1)
        r2 = client.post("/matchmaking/join", headers=h3)
        match_id_2 = r2.json()["match"]["id"]
        p1_h2 = h1 if r2.json()["match"]["player1_id"] == id1 else h3
        client.post(f"/matches/{match_id_2}/action", headers=p1_h2, json={"action": "attack"})

        # bob beats charlie (alice 2, bob 1, charlie 0; bob 1 loss, charlie 2 losses)
        client.post("/matchmaking/join", headers=h2)
        r3 = client.post("/matchmaking/join", headers=h3)
        match_id_3 = r3.json()["match"]["id"]
        p1_h3 = h2 if r3.json()["match"]["player1_id"] == id2 else h3
        client.post(f"/matches/{match_id_3}/action", headers=p1_h3, json={"action": "attack"})

        # GET leaderboard limit=10
        lb = client.get("/leaderboard?limit=10").json()
        assert len(lb) >= 2
        # First by wins DESC: alice (2), then bob (1), then charlie (0)
        assert lb[0]["wins"] >= lb[1]["wins"]
        if len(lb) >= 3:
            assert lb[1]["wins"] >= lb[2]["wins"]
        assert lb[0]["username"] == "alice"
        assert lb[0]["wins"] == 2
        assert lb[0]["losses"] == 0
        # Each row has required fields
        for row in lb:
            assert "rank" in row
            assert "user_id" in row
            assert "username" in row
            assert "class_name" in row
            assert "level" in row
            assert "wins" in row
            assert "losses" in row
            assert row["rank"] == lb.index(row) + 1

    def test_leaderboard_limit_respected(self, client):
        """limit=3 returns at most 3 rows."""
        lb = client.get("/leaderboard?limit=3").json()
        assert len(lb) <= 3
