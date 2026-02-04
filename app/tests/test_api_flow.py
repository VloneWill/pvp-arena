from datetime import datetime, timezone, timedelta

from app.db.models import Match
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
        """Test that Mage ability (fireball) damage is balanced and stronger than Power Strike."""
        import app.game.combat as combat
        monkeypatch.setattr(combat.random, "randint", lambda a, b: 20)

        h_mage = auth_headers(client, "user1", class_name="mage")
        h_warrior = auth_headers(client, "user2", class_name="warrior")

        client.post("/matchmaking/join", headers=h_mage)
        r = client.post("/matchmaking/join", headers=h_warrior)
        match_id = r.json()["match"]["id"]

        match_state = client.get(f"/matches/{match_id}/state", headers=h_mage).json()
        mage_id = my_user_id(client, h_mage)
        warrior_id = my_user_id(client, h_warrior)
        if match_state["current_turn"] == warrior_id:
            client.post(f"/matches/{match_id}/action", headers=h_warrior, json={"action": "attack"})

        # Mage uses fireball (1.3x), so 20 * 1.3 = 26
        r_action = client.post(f"/matches/{match_id}/action", headers=h_mage, json={"action": "fireball"})
        assert r_action.status_code == 200
        result = r_action.json()["result"]
        mage_damage = result["damage"]
        assert 24 <= mage_damage <= 28

        # New match: warrior power_strike (1.2x), 20 * 1.2 = 24
        client.post("/matchmaking/join", headers=h_mage)
        r2 = client.post("/matchmaking/join", headers=h_warrior)
        match_id2 = r2.json()["match"]["id"]
        match_state2 = client.get(f"/matches/{match_id2}/state", headers=h_mage).json()
        if match_state2["current_turn"] == mage_id:
            client.post(f"/matches/{match_id2}/action", headers=h_mage, json={"action": "attack"})
        r_action2 = client.post(f"/matches/{match_id2}/action", headers=h_warrior, json={"action": "power_strike"})
        assert r_action2.status_code == 200
        result2 = r_action2.json()["result"]
        power_strike_damage = result2["damage"]
        # Power Strike 1.35x on warrior 11-20 base -> ~15-27; test uses fixed randint 20 -> 27
        assert 22 <= power_strike_damage <= 30
        assert mage_damage >= power_strike_damage

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
        is_p1 = match_data["player1_id"] == id1
        p1_headers = h1 if is_p1 else h2
        p2_headers = h2 if is_p1 else h1
        cooldowns_key = "player1_cooldowns" if is_p1 else "player2_cooldowns"

        # Player 1 uses power_strike (cooldown 3); after turn advance it ticks to 2
        r1 = client.post(f"/matches/{match_id}/action", headers=p1_headers, json={"action": "power_strike"})
        assert r1.status_code == 200
        state1 = r1.json()["game_state"]
        cooldown1 = state1.get(cooldowns_key, {}).get("power_strike", 0)
        assert cooldown1 == 2

        # Player 2 acts
        client.post(f"/matches/{match_id}/action", headers=p2_headers, json={"action": "attack"})
        state2 = client.get(f"/matches/{match_id}/state", headers=p1_headers).json()
        cooldown2 = state2.get(cooldowns_key, {}).get("power_strike", 0)
        assert cooldown2 == 2

        # Try to use ability again - should fail
        r_fail = client.post(f"/matches/{match_id}/action", headers=p1_headers, json={"action": "power_strike"})
        assert r_fail.status_code == 400

        # Player 1 acts (attack) - turn ends, cooldown ticks to 1
        client.post(f"/matches/{match_id}/action", headers=p1_headers, json={"action": "attack"})
        client.post(f"/matches/{match_id}/action", headers=p2_headers, json={"action": "attack"})
        state3 = client.get(f"/matches/{match_id}/state", headers=p1_headers).json()
        cooldown3 = state3.get(cooldowns_key, {}).get("power_strike", 0)
        assert cooldown3 == 1

    def test_state_includes_action_tooltips(self, client):
        """Game state must include player1_action_tooltips and player2_action_tooltips with numeric values."""
        h1 = auth_headers(client, "warrior_a", class_name="warrior")
        h2 = auth_headers(client, "mage_b", class_name="mage")
        client.post("/matchmaking/join", headers=h1)
        r = client.post("/matchmaking/join", headers=h2)
        match_id = r.json()["match"]["id"]
        state = client.get(f"/matches/{match_id}/state", headers=h1).json()
        p1_tooltips = state.get("player1_action_tooltips", {})
        p2_tooltips = state.get("player2_action_tooltips", {})
        assert "attack" in p1_tooltips
        assert "attack" in p2_tooltips
        assert "damage_min" in p1_tooltips["attack"]
        assert "damage_max" in p1_tooltips["attack"]
        assert "defend" in p1_tooltips
        assert p1_tooltips["defend"].get("reduction_pct") == 50
        assert "heal" in p1_tooltips
        assert "heal_amount" in p1_tooltips["heal"]
        assert "power_strike" in p1_tooltips
        assert "fireball" in p2_tooltips

    def test_turn_timeout_tick_switches_turn(self, client, test_session_factory):
        """When turn_expires_at is in the past, POST /tick switches turn and resets timer."""
        h1 = auth_headers(client, "user1")
        h2 = auth_headers(client, "user2")
        id1 = my_user_id(client, h1)
        id2 = my_user_id(client, h2)

        client.post("/matchmaking/join", headers=h1)
        r = client.post("/matchmaking/join", headers=h2)
        match_id = r.json()["match"]["id"]
        match_data = r.json()["match"]
        p1_id = match_data["player1_id"]
        p2_id = match_data["player2_id"]

        db = test_session_factory()
        try:
            match = db.query(Match).filter(Match.id == match_id).first()
            assert match is not None
            match.current_turn = p1_id
            past = datetime.now(timezone.utc) - timedelta(seconds=10)
            match.turn_started_at = past
            match.turn_expires_at = past
            db.commit()
        finally:
            db.close()

        r_tick = client.post(f"/matches/{match_id}/tick", headers=h1)
        assert r_tick.status_code == 200
        body = r_tick.json()
        gs = body.get("game_state")
        assert gs is not None
        assert gs["current_turn"] == p2_id
        assert "turn_expires_at" in gs
        assert gs["turn_expires_at"] is not None
        raw = gs["turn_expires_at"].replace("Z", "+00:00")
        expires = datetime.fromisoformat(raw)
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        delta = (expires - now).total_seconds()
        assert 25 <= delta <= 35

    def test_turn_timeout_action_rejected_after_auto_switch(self, client, test_session_factory):
        """When turn has expired, action by the old current player is rejected as not their turn."""
        h1 = auth_headers(client, "user1")
        h2 = auth_headers(client, "user2")
        id1 = my_user_id(client, h1)
        id2 = my_user_id(client, h2)

        client.post("/matchmaking/join", headers=h1)
        r = client.post("/matchmaking/join", headers=h2)
        match_id = r.json()["match"]["id"]
        match_data = r.json()["match"]
        p1_id = match_data["player1_id"]

        db = test_session_factory()
        try:
            match = db.query(Match).filter(Match.id == match_id).first()
            match.current_turn = p1_id
            past = datetime.now(timezone.utc) - timedelta(seconds=10)
            match.turn_started_at = past
            match.turn_expires_at = past
            db.commit()
        finally:
            db.close()

        p1_headers = h1 if id1 == p1_id else h2
        r_action = client.post(
            f"/matches/{match_id}/action",
            headers=p1_headers,
            json={"action": "attack"},
        )
        assert r_action.status_code == 400
        assert "not your turn" in r_action.json().get("detail", "").lower() or "turn" in r_action.json().get("detail", "").lower()

    def test_profanity_username_rejected(self, client):
        """Registration with profane username returns 400 with disallowed language message."""
        r = client.post(
            "/auth/register",
            json={"username": "shithead", "password": "password123", "class_name": "warrior"},
        )
        assert r.status_code == 400
        assert r.json().get("detail") == "Username contains disallowed language."

    def test_disallowed_username_embedded_and_leetspeak(self, client):
        """Reject usernames with embedded offensive terms or leetspeak variants."""
        for bad in ("pussykid", "pu55y_kid"):
            r = client.post(
                "/auth/register",
                json={"username": bad, "password": "password123", "class_name": "warrior"},
            )
            assert r.status_code == 400, f"Expected 400 for username {bad!r}"
            assert r.json().get("detail") == "Username contains disallowed language."

    def test_allowed_username_accepted(self, client):
        """Normal usernames are accepted."""
        r = client.post(
            "/auth/register",
            json={"username": "player99", "password": "password123", "class_name": "warrior"},
        )
        assert r.status_code == 201
        assert r.json().get("username") == "player99"

    def test_username_length_and_chars_validated(self, client):
        """Username must be 3-20 chars and letters/numbers/underscore only."""
        r_short = client.post(
            "/auth/register",
            json={"username": "ab", "password": "password123", "class_name": "warrior"},
        )
        assert r_short.status_code in (400, 422)
        r_bad = client.post(
            "/auth/register",
            json={"username": "bad-name", "password": "password123", "class_name": "warrior"},
        )
        assert r_bad.status_code == 400
        detail = r_bad.json().get("detail", "").lower()
        assert "letters" in detail or "underscore" in detail or "character" in detail

    # Note: Database wipe test would require testing against actual SQLite file
    # This is better tested manually or as an integration test since unit tests use in-memory DB

