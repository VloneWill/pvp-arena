from app.tests.helpers import auth_headers, my_user_id


class TestAPIFullFlow:
    def test_matchmaking_creates_match(self, client):
        h1 = auth_headers(client, "user1")
        h2 = auth_headers(client, "user2")

        r1 = client.post("/matchmaking/join", headers=h1)
        assert r1.status_code == 200
        assert r1.json()["status"] == "waiting"

        r2 = client.post("/matchmaking/join", headers=h2)
        assert r2.status_code == 200
        body = r2.json()
        assert body["status"] == "matched"
        assert "match" in body
        assert body["match"]["status"] == "active"

    def test_turn_flow_attack_defend_state_updates(self, client, monkeypatch):
        # Make attack damage deterministic for this test
        import app.game.combat as combat

        monkeypatch.setattr(combat.random, "randint", lambda a, b: 20)

        h1 = auth_headers(client, "user1")
        h2 = auth_headers(client, "user2")

        id1 = my_user_id(client, h1)
        id2 = my_user_id(client, h2)

        client.post("/matchmaking/join", headers=h1)
        r = client.post("/matchmaking/join", headers=h2)
        match = r.json()["match"]
        match_id = match["id"]

        # Player1 should start (initialize_match sets current_turn = player1_id)
        # Figure out which header corresponds to match.player1_id
        if match["player1_id"] == id1:
            p1_headers, p2_headers = h1, h2
            p1_id, p2_id = id1, id2
        else:
            p1_headers, p2_headers = h2, h1
            p1_id, p2_id = id2, id1

        # P1 attacks
        r1 = client.post(f"/matches/{match_id}/action", headers=p1_headers, json={"action": "attack"})
        assert r1.status_code == 200
        gs = r1.json()["game_state"]
        assert gs["current_turn"] == p2_id
        assert gs["player1_health"] >= 0
        assert gs["player2_health"] >= 0

        # P1 tries to act again -> should be blocked (409 or 400 depending on rule violation)
        r_bad = client.post(f"/matches/{match_id}/action", headers=p1_headers, json={"action": "attack"})
        assert r_bad.status_code in (400, 409)

        # P2 defends
        r2 = client.post(f"/matches/{match_id}/action", headers=p2_headers, json={"action": "defend"})
        assert r2.status_code == 200
        gs2 = r2.json()["game_state"]
        assert gs2["current_turn"] == p1_id

        # P1 attacks again; since P2 defended, damage should be reduced (20 -> 10)
        r3 = client.post(f"/matches/{match_id}/action", headers=p1_headers, json={"action": "attack"})
        assert r3.status_code == 200
        result = r3.json()["result"]
        assert result["defended"] is True
        assert result["damage"] == 10

    def test_match_ends_cleanly(self, client, monkeypatch):
        # Force a one-hit kill to quickly test match end
        import app.game.combat as combat

        monkeypatch.setattr(combat.random, "randint", lambda a, b: 200)

        h1 = auth_headers(client, "user1")
        h2 = auth_headers(client, "user2")

        id1 = my_user_id(client, h1)
        id2 = my_user_id(client, h2)

        client.post("/matchmaking/join", headers=h1)
        r = client.post("/matchmaking/join", headers=h2)
        match = r.json()["match"]
        match_id = match["id"]

        if match["player1_id"] == id1:
            p1_headers = h1
            p1_id = id1
        else:
            p1_headers = h2
            p1_id = id2

        # P1 attacks and should end the match immediately
        r_end = client.post(f"/matches/{match_id}/action", headers=p1_headers, json={"action": "attack"})
        assert r_end.status_code == 200
        gs = r_end.json()["game_state"]
        assert gs["status"] == "finished"
        assert gs["winner_id"] == p1_id

        # After finished, no more actions allowed
        r_after = client.post(f"/matches/{match_id}/action", headers=p1_headers, json={"action": "attack"})
        assert r_after.status_code == 409

