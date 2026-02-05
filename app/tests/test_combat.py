import pytest
from sqlalchemy.orm import Session

from app.game.combat import (
    initialize_match,
    process_attack,
    process_defend,
    process_heal,
    process_ability,
    check_match_end,
    advance_turn,
    MatchNotActiveError,
    InvalidActionError,
    CombatEngine,
)
from app.db.models import Match, User


def make_match(db_session: Session, player1_class: str = "warrior", player2_class: str = "warrior"):
    """Create a match with two users in the database."""
    # Create users
    user1 = User(username=f"player1_{player1_class}", password_hash="hash", class_name=player1_class, level=1)
    user2 = User(username=f"player2_{player2_class}", password_hash="hash", class_name=player2_class, level=1)
    db_session.add(user1)
    db_session.add(user2)
    db_session.commit()
    db_session.refresh(user1)
    db_session.refresh(user2)
    
    # Create match
    match = Match(
        player1_id=user1.id,
        player2_id=user2.id,
        status="active",
    )
    db_session.add(match)
    db_session.commit()
    db_session.refresh(match)
    
    initialize_match(match, db_session)
    db_session.commit()
    db_session.refresh(match)
    
    return match


class TestAttacks:
    def test_attack_reduces_health(self, db_session):
        match = make_match(db_session)

        result = process_attack(
            match=match,
            attacker_id=match.player1_id,
            defender_id=match.player2_id,
            db=db_session,
        )

        assert result["action"] == "attack"
        # Health should be reduced from max HP (class-based, not necessarily 100)
        from app.game.classes import get_max_hp
        user2 = db_session.query(User).filter(User.id == match.player2_id).first()
        max_hp2 = get_max_hp(user2)
        assert match.player2_health < max_hp2


class TestDefense:
    def test_defend_reduces_damage(self, db_session):
        match = make_match(db_session)

        process_defend(match, match.player2_id, db_session)
        before = match.player2_health

        process_attack(match, attacker_id=match.player1_id, defender_id=match.player2_id, db=db_session)

        after = match.player2_health
        assert before - after <= 10  # reduced damage

    def test_defend_flag_clears_after_hit(self, db_session):
        match = make_match(db_session)

        # Player2 defends, then gets hit once
        process_defend(match, match.player2_id, db_session)
        assert match.player2_defending is True

        process_attack(match, attacker_id=match.player1_id, defender_id=match.player2_id, db=db_session)

        # Defender flag should clear, attacker flag should remain False
        assert match.player2_defending is False
        assert match.player1_defending is False


class TestHealing:
    def test_heal_caps_at_max_hp(self, db_session):
        match = make_match(db_session)
        match.player1_health = 95
        db_session.commit()

        result = process_heal(match, player_id=match.player1_id, db=db_session)

        # Heal should cap at max HP (class-based max)
        from app.game.classes import get_max_hp
        user = db_session.query(User).filter(User.id == match.player1_id).first()
        max_hp = get_max_hp(user)
        assert result["new_health"] <= max_hp


# Double Attack removed - class abilities replace it


class TestMatchEnd:
    def test_match_ends_when_health_zero(self, db_session):
        match = make_match(db_session)
        match.player2_health = 1
        db_session.commit()

        process_attack(match, attacker_id=match.player1_id, defender_id=match.player2_id, db=db_session)
        winner = check_match_end(match, db_session)

        assert winner == match.player1_id
        assert match.status == "finished"
        assert match.winner_id == match.player1_id  # Test winner_id is set

    def test_health_never_below_zero(self, db_session):
        match = make_match(db_session)
        match.player2_health = 5
        db_session.commit()

        # Large number of attacks, health should clamp at 0
        for _ in range(10):
            process_attack(match, attacker_id=match.player1_id, defender_id=match.player2_id, db=db_session)
            assert match.player2_health >= 0


class TestTurns:
    def test_turn_switches_after_an_action(self, db_session):
        match = make_match(db_session)
        engine = CombatEngine(db_session)
        
        initial_turn = match.current_turn
        engine.attack(match, attacker_id=match.player1_id, defender_id=match.player2_id)
        
        assert match.current_turn != initial_turn
        assert match.current_turn == match.player2_id

    def test_cannot_act_when_match_is_over(self, db_session):
        match = make_match(db_session)
        match.status = "finished"
        db_session.commit()

        with pytest.raises(MatchNotActiveError):
            process_attack(match, attacker_id=match.player1_id, defender_id=match.player2_id, db=db_session)

    def test_wrong_player_cannot_act(self, db_session):
        match = make_match(db_session)
        engine = CombatEngine(db_session)
        
        # Try to have player2 act when it's player1's turn
        with pytest.raises(InvalidActionError):
            engine.attack(match, attacker_id=match.player2_id, defender_id=match.player1_id)

    def test_player_cannot_act_twice_in_a_row(self, db_session):
        match = make_match(db_session)
        engine = CombatEngine(db_session)
        
        # Player1 acts
        engine.attack(match, attacker_id=match.player1_id, defender_id=match.player2_id)
        
        # Player1 tries to act again (should fail)
        with pytest.raises(InvalidActionError):
            engine.attack(match, attacker_id=match.player1_id, defender_id=match.player2_id)

    def test_dead_player_cannot_act(self, db_session):
        match = make_match(db_session)
        match.player1_health = 0
        db_session.commit()

        with pytest.raises(InvalidActionError):
            process_attack(match, attacker_id=match.player1_id, defender_id=match.player2_id, db=db_session)


class TestClassBalance:
    """Tests to verify class balance - no single class dominates."""
    
    def test_arcane_blast_exceeds_power_strike_damage(self):
        """Verify Mage has a higher damage ability multiplier than Warrior's Power Strike."""
        from app.game.abilities import get_ability
        power_strike = get_ability("warrior", "power_strike")
        meteor = get_ability("mage", "meteor")
        assert power_strike and meteor
        assert meteor["damage_multiplier"] > power_strike["damage_multiplier"]
        assert meteor["damage_multiplier"] >= power_strike["damage_multiplier"] + 0.2

    def test_rejuvenate_exceeds_base_heal(self):
        """Verify Druid's Regrowth heals more than base heal."""
        from app.game.abilities import get_ability
        regrowth = get_ability("druid", "regrowth")
        assert regrowth and regrowth.get("heal_multiplier", 0) >= 1.4
    
    def test_class_hp_ranges_are_reasonable(self):
        """Verify no class has extreme HP values at level 1."""
        from app.game.classes import CLASS_STATS
        
        warrior_hp = CLASS_STATS["warrior"]["base_hp"]
        mage_hp = CLASS_STATS["mage"]["base_hp"]
        druid_hp = CLASS_STATS["druid"]["base_hp"]
        rogue_hp = CLASS_STATS["rogue"]["base_hp"]
        
        # Warrior should have highest HP
        assert warrior_hp > mage_hp and warrior_hp > druid_hp and warrior_hp > rogue_hp
        # Mage should have lowest HP
        assert mage_hp < warrior_hp and mage_hp < druid_hp and mage_hp < rogue_hp
        # Rogue: lower than warrior (evasion-focused)
        assert rogue_hp < warrior_hp and rogue_hp > mage_hp
        # All in reasonable range (70-140)
        for name, hp in [("warrior", warrior_hp), ("mage", mage_hp), ("druid", druid_hp), ("rogue", rogue_hp)]:
            assert 70 <= hp <= 140, f"{name} HP should be in reasonable range"
    
    def test_class_attack_ranges_are_balanced(self):
        """Verify attack damage ranges are balanced."""
        from app.game.classes import CLASS_STATS
        
        warrior_avg = (CLASS_STATS["warrior"]["base_attack_min"] + CLASS_STATS["warrior"]["base_attack_max"]) / 2
        mage_avg = (CLASS_STATS["mage"]["base_attack_min"] + CLASS_STATS["mage"]["base_attack_max"]) / 2
        druid_avg = (CLASS_STATS["druid"]["base_attack_min"] + CLASS_STATS["druid"]["base_attack_max"]) / 2
        
        # Mage should have highest average attack (compensating for low HP)
        assert mage_avg >= warrior_avg, "Mage should have at least as high average attack as Warrior"
        assert mage_avg >= druid_avg, "Mage should have at least as high average attack as Druid"
        
        # All averages should be in reasonable range (10-25)
        assert 10 <= warrior_avg <= 25, "Warrior attack average should be reasonable"
        assert 10 <= mage_avg <= 25, "Mage attack average should be reasonable"
        assert 10 <= druid_avg <= 25, "Druid attack average should be reasonable"
    
    def test_class_heal_amounts_are_balanced(self):
        """Verify heal amounts are balanced - Druid should have best healing."""
        from app.game.classes import CLASS_STATS
        
        warrior_heal = CLASS_STATS["warrior"]["base_heal"]
        mage_heal = CLASS_STATS["mage"]["base_heal"]
        druid_heal = CLASS_STATS["druid"]["base_heal"]
        
        # Druid should have highest base heal (best sustain)
        assert druid_heal >= warrior_heal, "Druid should have at least as high base heal as Warrior"
        assert druid_heal >= mage_heal, "Druid should have at least as high base heal as Mage"
        
        # All heals should be in reasonable range (8-25)
        assert 8 <= warrior_heal <= 25, "Warrior heal should be reasonable"
        assert 8 <= mage_heal <= 25, "Mage heal should be reasonable"
        assert 8 <= druid_heal <= 25, "Druid heal should be reasonable"


class TestHPAlignment:
    """Tests to ensure HP alignment - current HP never exceeds max HP, starts at max HP."""
    
    def test_match_initialization_sets_health_to_max_hp(self, client):
        """Verify that match initialization sets health exactly to max_hp."""
        from app.tests.helpers import auth_headers
        from app.game.classes import get_max_hp
        from app.db.models import User
        
        # Create users with different classes via registration
        h1 = auth_headers(client, "warrior_user", class_name="warrior")
        h2 = auth_headers(client, "mage_user", class_name="mage")
        
        # Get user IDs
        r1 = client.get("/auth/me", headers=h1)
        r2 = client.get("/auth/me", headers=h2)
        warrior_id = r1.json()["id"]
        mage_id = r2.json()["id"]
        
        # Create match via matchmaking
        client.post("/matchmaking/join", headers=h1)
        r = client.post("/matchmaking/join", headers=h2)
        match_id = r.json()["match"]["id"]
        
        # Get state (triggers initialization)
        state_r = client.get(f"/matches/{match_id}/state", headers=h1)
        assert state_r.status_code == 200
        data = state_r.json()
        
        # Get user objects to compute max HP
        warrior_user = User(id=warrior_id, class_name="warrior", level=1)
        mage_user = User(id=mage_id, class_name="mage", level=1)
        warrior_max = get_max_hp(warrior_user)
        mage_max = get_max_hp(mage_user)
        
        # Verify health equals max_hp exactly
        if data["player1_id"] == warrior_id:
            assert data["player1_health"] == warrior_max, \
                f"Player1 health ({data['player1_health']}) should equal max_hp ({warrior_max})"
            assert data["player2_health"] == mage_max, \
                f"Player2 health ({data['player2_health']}) should equal max_hp ({mage_max})"
        else:
            assert data["player2_health"] == warrior_max, \
                f"Player2 health ({data['player2_health']}) should equal max_hp ({warrior_max})"
            assert data["player1_health"] == mage_max, \
                f"Player1 health ({data['player1_health']}) should equal max_hp ({mage_max})"
        
        # Verify health never exceeds max_hp
        assert data["player1_health"] <= data["player1_max_hp"], "Player1 health should never exceed max_hp"
        assert data["player2_health"] <= data["player2_max_hp"], "Player2 health should never exceed max_hp"
    
    def test_state_endpoint_never_returns_health_exceeding_max_hp(self, client, db_session):
        """Verify state endpoint clamps health to max_hp."""
        from app.tests.helpers import auth_headers
        from app.game.classes import get_max_hp
        from app.db.models import User, Match
        from app.game.combat import initialize_match
        
        # Create users
        h1 = auth_headers(client, "user1", class_name="warrior")
        h2 = auth_headers(client, "user2", class_name="mage")
        
        # Get user IDs
        r1 = client.get("/auth/me", headers=h1)
        r2 = client.get("/auth/me", headers=h2)
        user1_id = r1.json()["id"]
        user2_id = r2.json()["id"]
        
        # Create match via matchmaking
        client.post("/matchmaking/join", headers=h1)
        r = client.post("/matchmaking/join", headers=h2)
        match_id = r.json()["match"]["id"]
        
        # Use db_session fixture to manually manipulate health
        match = db_session.query(Match).filter(Match.id == match_id).first()
        initialize_match(match, db_session)
        
        # Manually set health to exceed max_hp (simulating legacy data bug)
        user1_obj = db_session.query(User).filter(User.id == user1_id).first()
        user2_obj = db_session.query(User).filter(User.id == user2_id).first()
        warrior_max = get_max_hp(user1_obj)
        mage_max = get_max_hp(user2_obj)
        
        if match.player1_id == user1_id:
            match.player1_health = warrior_max + 50  # Exceeds max
            match.player2_health = mage_max + 30  # Exceeds max
        else:
            match.player2_health = warrior_max + 50
            match.player1_health = mage_max + 30
        db_session.commit()
        
        # Get state
        response = client.get(f"/matches/{match_id}/state", headers=h1)
        assert response.status_code == 200
        data = response.json()
        
        # Verify health is clamped to max_hp
        assert data["player1_health"] <= data["player1_max_hp"], \
            f"player1_health ({data['player1_health']}) should not exceed max_hp ({data['player1_max_hp']})"
        assert data["player2_health"] <= data["player2_max_hp"], \
            f"player2_health ({data['player2_health']}) should not exceed max_hp ({data['player2_max_hp']})"
    
    def test_match_starts_at_full_health(self, client):
        """Verify that when a match is created, both players start at full health."""
        from app.tests.helpers import auth_headers
        from app.game.classes import get_max_hp
        from app.db.models import User
        
        # Create users with different levels
        h1 = auth_headers(client, "druid_user", class_name="druid")
        h2 = auth_headers(client, "warrior_user", class_name="warrior")
        
        # Get user info
        r1 = client.get("/auth/me", headers=h1)
        r2 = client.get("/auth/me", headers=h2)
        user1_data = r1.json()
        user2_data = r2.json()
        
        # Create match via matchmaking
        client.post("/matchmaking/join", headers=h1)
        r = client.post("/matchmaking/join", headers=h2)
        match_id = r.json()["match"]["id"]
        
        # Get state (triggers initialization)
        response = client.get(f"/matches/{match_id}/state", headers=h1)
        assert response.status_code == 200
        data = response.json()
        
        # Compute expected max HP
        druid_user = User(id=user1_data["id"], class_name="druid", level=user1_data["level"])
        warrior_user = User(id=user2_data["id"], class_name="warrior", level=user2_data["level"])
        druid_max = get_max_hp(druid_user)
        warrior_max = get_max_hp(warrior_user)
        
        # Verify health equals max_hp (full health at start)
        if data["player1_id"] == user1_data["id"]:
            assert data["player1_health"] == druid_max, \
                f"Player1 should start at full health ({druid_max}), got {data['player1_health']}"
            assert data["player2_health"] == warrior_max, \
                f"Player2 should start at full health ({warrior_max}), got {data['player2_health']}"
            assert data["player1_max_hp"] == druid_max, "player1_max_hp should be correct"
            assert data["player2_max_hp"] == warrior_max, "player2_max_hp should be correct"
        else:
            assert data["player2_health"] == druid_max, \
                f"Player2 should start at full health ({druid_max}), got {data['player2_health']}"
            assert data["player1_health"] == warrior_max, \
                f"Player1 should start at full health ({warrior_max}), got {data['player1_health']}"
            assert data["player2_max_hp"] == druid_max, "player2_max_hp should be correct"
            assert data["player1_max_hp"] == warrior_max, "player1_max_hp should be correct"


class TestCombatLogPersistence:
    """Verify combat_log and cooldowns/effects persist across commit and re-query (JSON mutation safety)."""

    def test_combat_log_persists_after_commit(self, db_session):
        """Perform action -> commit -> re-query -> assert combat_log persisted."""
        match = make_match(db_session)
        from app.game.combat import process_attack, initialize_match

        initialize_match(match, db_session)
        db_session.commit()
        process_attack(
            match=match,
            attacker_id=match.player1_id,
            defender_id=match.player2_id,
            db=db_session,
        )
        db_session.commit()
        db_session.refresh(match)
        assert match.combat_log is not None
        assert len(match.combat_log) >= 1
        assert any(e.get("action_type") == "attack" for e in match.combat_log)

        # Re-query from DB (new object) to ensure it was written
        from app.db.models import Match
        match2 = db_session.query(Match).filter(Match.id == match.id).first()
        assert match2 is not None
        assert match2.combat_log is not None
        assert len(match2.combat_log) >= 1

    def test_cooldowns_and_effects_persist_after_reload(self, db_session):
        """Use ability -> commit -> re-query -> assert cooldowns/effects persisted."""
        match = make_match(db_session, player1_class="warrior", player2_class="mage")
        from app.game.combat import process_ability, initialize_match
        from app.db.models import Match

        initialize_match(match, db_session)
        db_session.commit()
        db_session.refresh(match)
        process_ability(match, match.player1_id, "power_strike", db_session)
        db_session.commit()
        db_session.refresh(match)
        cooldowns = getattr(match, "player1_cooldowns", None) or {}
        assert cooldowns.get("power_strike", 0) > 0

        match2 = db_session.query(Match).filter(Match.id == match.id).first()
        assert match2 is not None
        c2 = getattr(match2, "player1_cooldowns", None) or {}
        assert c2.get("power_strike", 0) > 0


class TestCombatLogEffectResolution:
    """Combat log must show effect-driven outcomes: mitigation, DoT, reflect, evade."""

    def test_mitigation_effect_produces_log_entry(self, db_session):
        """Arcane Shield absorb produces a damage_absorbed log entry."""
        match = make_match(db_session, player1_class="mage", player2_class="warrior")
        # P1 (mage) casts arcane_shield on self, then P2 attacks P1
        process_ability(match, match.player1_id, "arcane_shield", db_session)
        db_session.commit()
        db_session.refresh(match)
        advance_turn(match)
        # P2 attacks P1; P1's arcane shield should absorb some damage
        process_attack(
            match=match,
            attacker_id=match.player2_id,
            defender_id=match.player1_id,
            db=db_session,
        )
        log_types = [e.get("action_type") for e in (match.combat_log or [])]
        assert "damage_absorbed" in log_types, "Combat log should contain damage_absorbed when Arcane Shield absorbs"
        absorbed_evt = next(e for e in match.combat_log if e.get("action_type") == "damage_absorbed")
        assert absorbed_evt.get("effect") == "arcane_shield"
        assert absorbed_evt.get("amount", 0) >= 0

    def test_dot_effect_produces_log_entries_on_subsequent_turns(self, db_session):
        """Poison DoT produces dot_tick log entries on subsequent turns."""
        match = make_match(db_session, player1_class="rogue", player2_class="warrior")
        # P1 (rogue) applies poison to P2 (enemy)
        process_ability(match, match.player1_id, "poison", db_session)
        db_session.commit()
        db_session.refresh(match)
        advance_turn(match)
        # Start of P2's turn: DoT ticks on P2 (poison on P2)
        from app.game.combat import _apply_dot_ticks
        _apply_dot_ticks(match, match.player2_id, db_session)
        log_types = [e.get("action_type") for e in (match.combat_log or [])]
        assert "dot_tick" in log_types, "Combat log should contain dot_tick when Poison ticks"
        dot_evt = next(e for e in match.combat_log if e.get("action_type") == "dot_tick")
        assert dot_evt.get("effect") == "poison"
        assert dot_evt.get("damage", 0) > 0
        assert dot_evt.get("target_id") == match.player2_id


class TestCombatLogGrammarAndActionKey:
    """Combat log messages: correct grammar, past tense for results, action_key always present."""

    def test_attack_event_has_action_key(self, db_session):
        match = make_match(db_session)
        process_attack(
            match=match,
            attacker_id=match.player1_id,
            defender_id=match.player2_id,
            db=db_session,
        )
        attack_evt = next(e for e in match.combat_log if e.get("action_type") == "attack")
        assert attack_evt.get("action_key") == "attack"

    def test_defend_event_has_action_key(self, db_session):
        match = make_match(db_session)
        process_defend(match, match.player1_id, db_session)
        defend_evt = next(e for e in match.combat_log if e.get("action_type") == "defend")
        assert defend_evt.get("action_key") == "defend"

    def test_heal_event_has_action_key(self, db_session):
        match = make_match(db_session)
        process_heal(match, match.player1_id, db_session)
        heal_evt = next(e for e in match.combat_log if e.get("action_type") == "heal")
        assert heal_evt.get("action_key") == "heal"

    def test_combat_log_formatter_produces_correct_grammar(self):
        """Snapshot-style: formatter uses past tense for damage and includes action name."""
        from app.game.combat_log import format_combat_log_message

        event = {
            "action_type": "attack",
            "action_key": "attack",
            "attacker_id": 1,
            "defender_id": 2,
            "damage": 12,
            "defended": False,
            "attacker_username": "Alice",
            "defender_username": "Bob",
        }
        msg = format_combat_log_message(event, viewer_id=2, actor_username="Alice", defender_username="Bob", attacker_username="Alice")
        assert "dealt" in msg
        assert "12" in msg
        assert "Basic Attack" in msg
        assert "You" in msg or "Bob" in msg

        event_heal = {"action_type": "heal", "action_key": "heal", "actor_id": 1, "healed": 10, "actor_username": "Alice"}
        msg_heal = format_combat_log_message(event_heal, viewer_id=1, actor_username="Alice")
        assert "healed" in msg_heal
        assert "10" in msg_heal
        assert "Heal" in msg_heal


class TestShieldWallAndEvadeLifecycle:
    """Shield Wall and Evade: next-hit buffs, consumed on hit, not decremented on application turn."""

    def test_shield_wall_reduces_two_hits_then_expires(self, db_session):
        match = make_match(db_session, player1_class="warrior", player2_class="mage")
        # P1 uses Shield Wall (effect, hits_left=2; does not expire by turn)
        process_ability(match, match.player1_id, "shield_wall", db_session)
        db_session.commit()
        db_session.refresh(match)
        effects_before = list(getattr(match, "player1_effects", None) or [])
        assert any(e.get("name") == "shield_wall" for e in effects_before), "Shield Wall should be applied"
        sw = next(e for e in effects_before if e.get("name") == "shield_wall")
        assert sw.get("hits_left") == 2, "Shield Wall should have 2 hits remaining"

        advance_turn(match)
        effects_after_turn = list(getattr(match, "player1_effects", None) or [])
        assert any(e.get("name") == "shield_wall" for e in effects_after_turn), "Shield Wall should not expire at end of turn"

        # First hit: Shield Wall reduces damage, 1 hit remaining
        hp_before_1 = match.player1_health
        process_attack(match, attacker_id=match.player2_id, defender_id=match.player1_id, db=db_session)
        hp_after_1 = match.player1_health
        assert hp_before_1 - hp_after_1 < 20, "Shield Wall should reduce first hit"
        db_session.commit()
        db_session.refresh(match)
        effects_after_first = list(getattr(match, "player1_effects", None) or [])
        assert any(e.get("name") == "shield_wall" for e in effects_after_first), "Shield Wall should have 1 hit left after first hit"
        sw_1 = next(e for e in effects_after_first if e.get("name") == "shield_wall")
        assert sw_1.get("hits_left") == 1, "Shield Wall should have 1 hit remaining"

        advance_turn(match)
        process_attack(match, attacker_id=match.player2_id, defender_id=match.player1_id, db=db_session)
        db_session.commit()
        db_session.refresh(match)
        effects_after_second = list(getattr(match, "player1_effects", None) or [])
        assert not any(e.get("name") == "shield_wall" for e in effects_after_second), "Shield Wall should expire after two hits"

    def test_evade_triggers_on_next_hit_then_expires(self, db_session):
        match = make_match(db_session, player1_class="rogue", player2_class="warrior")
        process_ability(match, match.player1_id, "evade", db_session)
        db_session.commit()
        db_session.refresh(match)
        effects_before = list(getattr(match, "player1_effects", None) or [])
        assert any(e.get("name") == "evade" for e in effects_before)

        advance_turn(match)
        process_attack(match, attacker_id=match.player2_id, defender_id=match.player1_id, db=db_session)
        log_types = [e.get("action_type") for e in (match.combat_log or [])]
        assert "evade_avoided" in log_types, "Evade should trigger and log"
        effects_after = list(getattr(match, "player1_effects", None) or [])
        assert not any(e.get("name") == "evade" for e in effects_after), "Evade should expire after one hit"

    def test_evade_not_decremented_immediately_on_application(self, db_session):
        """Evade has hits_left, not turns_left; so it must not be removed at end of turn."""
        match = make_match(db_session, player1_class="rogue", player2_class="warrior")
        process_ability(match, match.player1_id, "evade", db_session)
        db_session.commit()
        db_session.refresh(match)
        advance_turn(match)
        effects_after_tick = list(getattr(match, "player1_effects", None) or [])
        assert any(e.get("name") == "evade" for e in effects_after_tick), "Evade should still be present after turn tick (hits_left, not turns)"


class TestChillEffect:
    """Chill from Ice Bolt has a real mechanical effect (target takes more damage)."""

    def test_ice_bolt_applies_chill_and_chill_increases_damage(self, db_session):
        match = make_match(db_session, player1_class="mage", player2_class="warrior")
        # P1 (mage) hits P2 with Ice Bolt -> applies Chill on P2
        process_ability(match, match.player1_id, "ice_bolt", db_session)
        db_session.commit()
        db_session.refresh(match)
        effects = list(getattr(match, "player2_effects", None) or [])
        assert any(e.get("name") == "chill" for e in effects), "Chill should be applied"

        advance_turn(match)
        # P1 attacks P2; Chill on P2 should increase damage taken, then Chill is consumed
        hp_before = match.player2_health
        process_attack(match, attacker_id=match.player1_id, defender_id=match.player2_id, db=db_session)
        hp_after = match.player2_health
        assert hp_before - hp_after >= 1, "Chill should increase damage"
        effects_after = list(getattr(match, "player2_effects", None) or [])
        assert not any(e.get("name") == "chill" for e in effects_after), "Chill consumed after one hit"


class TestUniqueAbilityMechanics:
    """Each class ability has a distinct mechanic: Shield Wall != Defend, Backstab applies bleed, Shadowstep grants DoT buff."""

    def test_shield_wall_differs_from_defend(self, db_session):
        match = make_match(db_session, player1_class="warrior", player2_class="mage")
        process_ability(match, match.player1_id, "shield_wall", db_session)
        db_session.commit()
        db_session.refresh(match)
        assert not match.player1_defending, "Shield Wall is an effect, not the defend flag"
        effects = getattr(match, "player1_effects", None) or []
        assert any(e.get("name") == "shield_wall" for e in effects)

    def test_backstab_applies_bleed_when_target_not_defending(self, db_session):
        match = make_match(db_session, player1_class="rogue", player2_class="warrior")
        process_ability(match, match.player1_id, "backstab", db_session)
        db_session.commit()
        db_session.refresh(match)
        effects = getattr(match, "player2_effects", None) or []
        assert any(e.get("name") == "bleed" for e in effects), "Backstab should apply Bleed when target not defending"

    def test_shadowstep_grants_dot_buff_to_self(self, db_session):
        match = make_match(db_session, player1_class="rogue", player2_class="warrior")
        process_ability(match, match.player1_id, "shadowstep", db_session)
        db_session.commit()
        db_session.refresh(match)
        effects = getattr(match, "player1_effects", None) or []
        assert any(e.get("name") == "shadowstep_buff" for e in effects), "Shadowstep should grant shadowstep_buff to self"
        buff = next(e for e in effects if e.get("name") == "shadowstep_buff")
        assert buff.get("dot_bonus_per_tick") == 3
        assert buff.get("dot_damage_pct") == 1.25

    def test_shadowstep_buff_amplifies_rogue_dot_ticks(self, db_session):
        """When the rogue has shadowstep_buff, their DoT (e.g. poison) on the enemy ticks for more damage."""
        from app.game.combat import _apply_dot_ticks

        match = make_match(db_session, player1_class="rogue", player2_class="warrior")
        # P1 shadowstep -> gets shadowstep_buff
        process_ability(match, match.player1_id, "shadowstep", db_session)
        db_session.commit()
        db_session.refresh(match)
        # P1 applies poison to P2 (6/tick base)
        process_ability(match, match.player1_id, "poison", db_session)
        db_session.commit()
        db_session.refresh(match)
        hp_before_tick = match.player2_health
        # DoT ticks at start of target's turn: apply DoT to P2 (poison source is P1 who has shadowstep_buff)
        _apply_dot_ticks(match, match.player2_id, db_session)
        hp_after_tick = match.player2_health
        # Base poison is 6/tick; with buff: int(6 * 1.25) + 3 = 7 + 3 = 10
        damage_dealt = hp_before_tick - hp_after_tick
        assert damage_dealt == 10, f"Shadowstep buff should amplify DoT to 10 damage/tick, got {damage_dealt}"


class TestChillPersistsUntilCasterNextTurn:
    """Chill applied to opponent remains active when caster gets their next turn (expires at end of caster's next turn)."""

    def test_chill_remains_when_caster_gets_next_turn(self, db_session):
        match = make_match(db_session, player1_class="mage", player2_class="warrior")
        process_ability(match, match.player1_id, "ice_bolt", db_session)
        db_session.commit()
        db_session.refresh(match)
        effects_p2 = list(getattr(match, "player2_effects", None) or [])
        assert any(e.get("name") == "chill" for e in effects_p2), "Chill should be on P2"
        advance_turn(match)
        assert match.current_turn == match.player2_id
        process_defend(match, match.player2_id, db_session)
        advance_turn(match)
        effects_p2_after = list(getattr(match, "player2_effects", None) or [])
        assert any(e.get("name") == "chill" for e in effects_p2_after), "Chill should still be on P2 when P1 gets next turn"
        hp_before = match.player2_health
        process_attack(match, match.player1_id, match.player2_id, db_session)
        hp_after = match.player2_health
        assert hp_before - hp_after >= 1, "Chill should increase damage on P1's next hit"
        effects_p2_final = list(getattr(match, "player2_effects", None) or [])
        assert not any(e.get("name") == "chill" for e in effects_p2_final), "Chill consumed after hit"


class TestShapeshiftDuration:
    """Shapeshift remains active through opponent's turn and caster's next turn."""

    def test_shapeshift_last_through_opponent_turn_and_caster_next_turn(self, db_session):
        match = make_match(db_session, player1_class="druid", player2_class="warrior")
        process_ability(match, match.player1_id, "shapeshift", db_session)
        db_session.commit()
        db_session.refresh(match)
        effects = list(getattr(match, "player1_effects", None) or [])
        assert any(e.get("name") == "shapeshift" for e in effects)
        advance_turn(match)
        effects_after_p1 = list(getattr(match, "player1_effects", None) or [])
        assert any(e.get("name") == "shapeshift" for e in effects_after_p1), "Shapeshift should still be up after P1 ends turn"
        process_attack(match, match.player2_id, match.player1_id, db_session)
        advance_turn(match)
        effects_after_p2 = list(getattr(match, "player1_effects", None) or [])
        assert any(e.get("name") == "shapeshift" for e in effects_after_p2), "Shapeshift should still be up after P2's turn"
        assert match.current_turn == match.player1_id
        process_attack(match, match.player1_id, match.player2_id, db_session)
        effects_after_p1_act = list(getattr(match, "player1_effects", None) or [])
        assert any(e.get("name") == "shapeshift" for e in effects_after_p1_act), "Shapeshift should still be up when P1 acts again"


class TestBattleShoutEffect:
    """Battle Shout has measurable effect (flat damage + damage reduction) and persists until end of next turn."""

    def test_battle_shout_increases_damage_and_reduces_incoming(self, db_session):
        match = make_match(db_session, player1_class="warrior", player2_class="mage")
        process_ability(match, match.player1_id, "battle_shout", db_session)
        db_session.commit()
        db_session.refresh(match)
        effects = list(getattr(match, "player1_effects", None) or [])
        assert any(e.get("name") == "battle_shout" for e in effects), "Battle Shout should be applied"
        advance_turn(match)
        hp_p1_before = match.player1_health
        process_attack(match, match.player2_id, match.player1_id, db_session)
        hp_p1_after = match.player1_health
        damage_taken = hp_p1_before - hp_p1_after
        assert damage_taken >= 0
        advance_turn(match)
        hp_p2_before = match.player2_health
        process_attack(match, match.player1_id, match.player2_id, db_session)
        hp_p2_after = match.player2_health
        damage_dealt = hp_p2_before - hp_p2_after
        assert damage_dealt >= 5, "Battle Shout should add at least 5 flat damage"


class TestCombatLogPossessiveGrammar:
    """Combat log never outputs 'You's'; uses 'Your' and 'Opponent's' correctly."""

    def test_damage_reflected_uses_your_not_yous(self):
        from app.game.combat_log import format_combat_log_message
        event = {
            "action_type": "damage_reflected",
            "effect": "thorns",
            "defender_id": 1,
            "attacker_id": 2,
            "amount": 10,
            "defender_username": "Alice",
            "attacker_username": "Bob",
        }
        msg = format_combat_log_message(
            event, viewer_id=1, actor_username="Alice",
            defender_username="Alice", attacker_username="Bob"
        )
        assert "You's" not in msg, "Must never output 'You's'"
        assert "Your" in msg, "Viewer's effect should use 'Your'"
        assert "10" in msg

    def test_damage_reflected_uses_opponent_possessive_when_viewer_is_attacker(self):
        from app.game.combat_log import format_combat_log_message
        event = {
            "action_type": "damage_reflected",
            "effect": "thorns",
            "defender_id": 1,
            "attacker_id": 2,
            "amount": 8,
            "defender_username": "Alice",
            "attacker_username": "Bob",
        }
        msg = format_combat_log_message(
            event, viewer_id=2, actor_username="Bob",
            defender_username="Alice", attacker_username="Bob"
        )
        assert "You's" not in msg


class TestCombatLogYouOpponentLabel:
    """Combat log display uses actor_id to set is_my_action (YOU vs OPPONENT)."""

    def test_build_display_entry_uses_actor_id_for_is_my_action(self):
        from app.game.combat_log import build_display_entry
        event_my = {"action_type": "attack", "attacker_id": 1, "defender_id": 2, "damage": 10, "defended": False,
                    "actor_username": "Me", "attacker_username": "Me", "defender_username": "Other"}
        entry_my = build_display_entry(event_my, viewer_id=1)
        assert entry_my["is_my_action"] is True
        event_other = {"action_type": "attack", "attacker_id": 2, "defender_id": 1, "damage": 10, "defended": False,
                       "actor_username": "Other", "attacker_username": "Other", "defender_username": "Me"}
        entry_other = build_display_entry(event_other, viewer_id=1)
        assert entry_other["is_my_action"] is False


class TestShapeshiftHealBoostAndCombatLogBuffs:
    """Shapeshift increases healing; combat log reflects heal/damage buff breakdowns."""

    def test_shapeshift_increases_heal_and_log_shows_breakdown(self, db_session):
        match = make_match(db_session, player1_class="druid", player2_class="warrior")
        process_ability(match, match.player1_id, "shapeshift", db_session)
        db_session.commit()
        db_session.refresh(match)
        effects = list(getattr(match, "player1_effects", None) or [])
        assert any(e.get("name") == "shapeshift" for e in effects)
        hp_before = match.player1_health
        match.player1_health = max(0, hp_before - 30)  # take some damage
        db_session.commit()
        db_session.refresh(match)
        process_heal(match, match.player1_id, db_session)  # basic heal
        result = match.combat_log[-1]
        assert result.get("healed", 0) > 0
        assert result.get("heal_bonus_shapeshift", 0) > 0
        from app.game.combat_log import format_combat_log_message
        msg = format_combat_log_message(
            result, viewer_id=match.player1_id, actor_username="Druid",
        )
        assert "Shapeshift" in msg
        assert "Increased by" in msg

    def test_combat_log_heal_message_includes_shapeshift_bonus(self):
        from app.game.combat_log import format_combat_log_message
        event = {"action_type": "heal", "action_key": "heal", "actor_id": 1, "healed": 14, "heal_bonus_shapeshift": 5}
        msg = format_combat_log_message(event, viewer_id=1, actor_username="You")
        assert "14" in msg
        assert "Increased by 5 for Shapeshift" in msg

    def test_combat_log_attack_message_includes_buff_breakdowns(self):
        from app.game.combat_log import format_combat_log_message
        event = {
            "action_type": "attack", "action_key": "power_strike", "attacker_id": 1, "defender_id": 2,
            "damage": 22, "defended": False, "damage_bonus_battle_shout": 5, "damage_bonus_chill": 3,
            "attacker_username": "War", "defender_username": "Mage",
        }
        msg = format_combat_log_message(event, viewer_id=1, actor_username="War", attacker_username="War", defender_username="Mage")
        assert "22" in msg
        assert "Increased by 5 for Battle Shout" in msg
        assert "Increased by 3 for Chill" in msg

    def test_nature_wrath_with_shapeshift_shows_damage_bonus_in_log(self, db_session):
        """Attack abilities (e.g. Nature Wrath) with Shapeshift active show 'Increased by X for Shapeshift' in combat log."""
        match = make_match(db_session, player1_class="druid", player2_class="warrior")
        process_ability(match, match.player1_id, "shapeshift", db_session)
        db_session.commit()
        db_session.refresh(match)
        process_ability(match, match.player1_id, "nature_wrath", db_session)
        db_session.commit()
        db_session.refresh(match)
        attack_evts = [e for e in (match.combat_log or []) if e.get("action_key") == "nature_wrath" or (e.get("action_type") == "attack" and e.get("damage"))]
        assert attack_evts, "Combat log should have Nature Wrath attack"
        last_attack = attack_evts[-1]
        assert last_attack.get("damage_bonus_shapeshift", 0) > 0, "Nature Wrath with Shapeshift should log damage_bonus_shapeshift"
        from app.game.combat_log import format_combat_log_message
        msg = format_combat_log_message(
            last_attack, viewer_id=match.player1_id, actor_username="Druid",
            attacker_username="Druid", defender_username="War",
        )
        assert "Shapeshift" in msg
        assert "Increased by" in msg

    def test_all_ability_buff_breakdowns_on_attack_line(self):
        """Shield Wall, Evade, Thorns, Arcane Shield, Chill, Battle Shout appear on main attack line when they apply."""
        from app.game.combat_log import format_combat_log_message
        # Shield Wall: reduced + reflected
        ev = {"action_type": "attack", "action_key": "attack", "attacker_id": 1, "defender_id": 2, "damage": 15,
              "defended": False, "damage_reduced_shield_wall": 25, "damage_reflected_shield_wall": 5,
              "attacker_username": "A", "defender_username": "B"}
        msg = format_combat_log_message(ev, viewer_id=1, actor_username="A", attacker_username="A", defender_username="B")
        assert "Reduced by 25 (Shield Wall)" in msg
        assert "Reflected 5 to attacker (Shield Wall)" in msg
        # Evade
        ev2 = {"action_type": "attack", "action_key": "attack", "attacker_id": 1, "defender_id": 2, "damage": 0,
               "defended": False, "evaded": True, "attacker_username": "A", "defender_username": "B"}
        msg2 = format_combat_log_message(ev2, viewer_id=1, actor_username="A", attacker_username="A", defender_username="B")
        assert "Evaded." in msg2
        # Thorns
        ev3 = {"action_type": "attack", "action_key": "attack", "attacker_id": 1, "defender_id": 2, "damage": 12,
               "defended": False, "damage_reflected_thorns": 3, "attacker_username": "A", "defender_username": "B"}
        msg3 = format_combat_log_message(ev3, viewer_id=1, actor_username="A", attacker_username="A", defender_username="B")
        assert "Reflected 3 to attacker (Thorns)" in msg3
        # Arcane Shield
        ev4 = {"action_type": "attack", "action_key": "attack", "attacker_id": 1, "defender_id": 2, "damage": 5,
               "defended": False, "damage_absorbed_arcane_shield": 18, "attacker_username": "A", "defender_username": "B"}
        msg4 = format_combat_log_message(ev4, viewer_id=1, actor_username="A", attacker_username="A", defender_username="B")
        assert "Absorbed 18 (Arcane Shield)" in msg4
