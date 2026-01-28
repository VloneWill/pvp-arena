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

    def test_both_players_see_match_automatically(self, client):
        """Test that both players see the match when it's created without refresh."""
        h1 = auth_headers(client, "user1")
        h2 = auth_headers(client, "user2")

        # Player 1 joins matchmaking
        r1 = client.post("/matchmaking/join", headers=h1)
        assert r1.status_code == 200
        assert r1.json()["status"] == "waiting"

        # Player 2 joins matchmaking - match should be created
        r2 = client.post("/matchmaking/join", headers=h2)
        assert r2.status_code == 200
        body2 = r2.json()
        assert body2["status"] == "matched"
        assert "match" in body2
        match_id = body2["match"]["id"]

        # Player 1 should also see the match when they poll
        r1_poll = client.post("/matchmaking/join", headers=h1)
        assert r1_poll.status_code == 200
        body1_poll = r1_poll.json()
        assert body1_poll["status"] == "matched"
        assert "match" in body1_poll
        assert body1_poll["match"]["id"] == match_id

    def test_xp_awarded_after_match_end(self, client, monkeypatch):
        """Test that XP is awarded to both players after match ends."""
        import app.game.combat as combat
        monkeypatch.setattr(combat.random, "randint", lambda a, b: 200)

        h1 = auth_headers(client, "user1", class_name="warrior")
        h2 = auth_headers(client, "user2", class_name="mage")

        id1 = my_user_id(client, h1)
        id2 = my_user_id(client, h2)

        # Get initial XP
        me1_before = client.get("/auth/me", headers=h1).json()
        me2_before = client.get("/auth/me", headers=h2).json()
        xp1_before = me1_before.get("xp", 0)
        xp2_before = me2_before.get("xp", 0)

        # Create match
        client.post("/matchmaking/join", headers=h1)
        r = client.post("/matchmaking/join", headers=h2)
        match_id = r.json()["match"]["id"]

        # Determine which player is player1
        match_data = client.get(f"/matches/{match_id}", headers=h1).json()
        if match_data["player1_id"] == id1:
            p1_headers = h1
        else:
            p1_headers = h2

        # End match with one attack
        r_end = client.post(f"/matches/{match_id}/action", headers=p1_headers, json={"action": "attack"})
        state_after = r_end.json()["game_state"]
        winner_id = state_after["winner_id"]

        # Check XP was awarded
        me1_after = client.get("/auth/me", headers=h1).json()
        me2_after = client.get("/auth/me", headers=h2).json()
        
        # Winner gets 50 XP, loser gets 20 XP
        if winner_id == id1:
            assert me1_after["xp"] == xp1_before + 50
            assert me2_after["xp"] == xp2_before + 20
        else:
            assert me1_after["xp"] == xp1_before + 20
            assert me2_after["xp"] == xp2_before + 50

    def test_arcane_blast_damage_balanced(self, client, monkeypatch):
        """Test that Arcane Blast damage is balanced (1.4x multiplier) and stronger than Power Strike."""
        import app.game.combat as combat
        # Set deterministic damage
        monkeypatch.setattr(combat.random, "randint", lambda a, b: 20)

        h1 = auth_headers(client, "user1", class_name="mage")
        h2 = auth_headers(client, "user2", class_name="warrior")

        client.post("/matchmaking/join", headers=h1)
        r = client.post("/matchmaking/join", headers=h2)
        match_id = r.json()["match"]["id"]

        # Get match to determine player order
        match_data = client.get(f"/matches/{match_id}", headers=h1).json()
        id1 = my_user_id(client, h1)
        
        if match_data["player1_id"] == id1:
            p1_headers = h1
            p2_headers = h2
        else:
            p1_headers = h2
            p2_headers = h1

        # Use Arcane Blast (should be 1.4x damage, so 20 * 1.4 = 28)
        r_action = client.post(f"/matches/{match_id}/action", headers=p1_headers, json={"action": "arcane_blast"})
        assert r_action.status_code == 200
        
        result = r_action.json()["result"]
        arcane_damage = result["damage"]
        # Arcane Blast should deal ~28 damage (20 base * 1.4 multiplier)
        assert 26 <= arcane_damage <= 30

        # Now test Power Strike (should be weaker, 1.25x damage, so 20 * 1.25 = 25)
        # Reset match state by creating a new match
        client.post("/matchmaking/join", headers=h1)
        r2 = client.post("/matchmaking/join", headers=h2)
        match_id2 = r2.json()["match"]["id"]
        match_data2 = client.get(f"/matches/{match_id2}", headers=h1).json()
        
        if match_data2["player1_id"] == id1:
            p1_headers2 = h1
        else:
            p1_headers2 = h2

        r_action2 = client.post(f"/matches/{match_id2}/action", headers=p1_headers2, json={"action": "power_strike"})
        assert r_action2.status_code == 200
        
        result2 = r_action2.json()["result"]
        power_strike_damage = result2["damage"]
        # Power Strike should deal ~25 damage (20 base * 1.25 multiplier)
        assert 23 <= power_strike_damage <= 27
        
        # Arcane Blast should be stronger than Power Strike
        assert arcane_damage > power_strike_damage

    def test_cooldown_persists_across_turns(self, client, monkeypatch):
        """Test that ability cooldowns persist correctly across multiple turns."""
        import app.game.combat as combat
        monkeypatch.setattr(combat.random, "randint", lambda a, b: 10)

        h1 = auth_headers(client, "user1", class_name="warrior")
        h2 = auth_headers(client, "user2", class_name="mage")

        client.post("/matchmaking/join", headers=h1)
        r = client.post("/matchmaking/join", headers=h2)
        match_id = r.json()["match"]["id"]

        match_data = client.get(f"/matches/{match_id}", headers=h1).json()
        id1 = my_user_id(client, h1)
        
        if match_data["player1_id"] == id1:
            p1_headers = h1
            p2_headers = h2
        else:
            p1_headers = h2
            p2_headers = h1

        # Player 1 uses ability
        r1 = client.post(f"/matches/{match_id}/action", headers=p1_headers, json={"action": "power_strike"})
        assert r1.status_code == 200
        state1 = r1.json()["game_state"]
        # Cooldown should be set (3 turns)
        cooldown1 = state1["player1_ability_cooldown"] if match_data["player1_id"] == id1 else state1["player2_ability_cooldown"]
        assert cooldown1 == 3

        # Player 2 acts
        client.post(f"/matches/{match_id}/action", headers=p2_headers, json={"action": "attack"})
        
        # Player 1's turn again - cooldown should still be 3 (only decrements when player 1's turn ends)
        state2 = client.get(f"/matches/{match_id}/state", headers=p1_headers).json()
        cooldown2 = state2["player1_ability_cooldown"] if match_data["player1_id"] == id1 else state2["player2_ability_cooldown"]
        assert cooldown2 == 3  # Cooldown doesn't decrease on opponent's turn

        # Try to use ability again - should fail
        r_fail = client.post(f"/matches/{match_id}/action", headers=p1_headers, json={"action": "power_strike"})
        assert r_fail.status_code == 400  # Should be blocked by cooldown
        
        # Player 1 acts (any action) - this ends their turn, cooldown should decrement to 2
        client.post(f"/matches/{match_id}/action", headers=p1_headers, json={"action": "attack"})
        
        # Player 2 acts
        client.post(f"/matches/{match_id}/action", headers=p2_headers, json={"action": "attack"})
        
        # Player 1's turn again - cooldown should be 2 now (decremented when player 1's turn ended)
        state3 = client.get(f"/matches/{match_id}/state", headers=p1_headers).json()
        cooldown3 = state3["player1_ability_cooldown"] if match_data["player1_id"] == id1 else state3["player2_ability_cooldown"]
        assert cooldown3 == 2

    # Note: Database wipe test would require testing against actual SQLite file
    # This is better tested manually or as an integration test since unit tests use in-memory DB

