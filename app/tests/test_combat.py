import pytest
from sqlalchemy.orm import Session

from app.game.combat import (
    initialize_match,
    process_attack,
    process_defend,
    process_heal,
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
        """Verify Mage's Arcane Blast has higher damage multiplier than Warrior's Power Strike."""
        from app.game.combat import MAGE_ARCANE_BLAST_MULTIPLIER, WARRIOR_POWER_STRIKE_MULTIPLIER
        assert MAGE_ARCANE_BLAST_MULTIPLIER > WARRIOR_POWER_STRIKE_MULTIPLIER, \
            "Arcane Blast should have higher multiplier than Power Strike"
        # Verify the gap is meaningful (at least 0.2x difference)
        assert MAGE_ARCANE_BLAST_MULTIPLIER >= WARRIOR_POWER_STRIKE_MULTIPLIER + 0.2
    
    def test_rejuvenate_exceeds_base_heal(self):
        """Verify Druid's Rejuvenate heals more than base heal."""
        from app.game.combat import DRUID_REJUVENATE_MULTIPLIER
        # Rejuvenate should be at least 1.4x base heal
        assert DRUID_REJUVENATE_MULTIPLIER >= 1.4, \
            "Rejuvenate should have meaningful multiplier over base heal"
    
    def test_class_hp_ranges_are_reasonable(self):
        """Verify no class has extreme HP values at level 1."""
        from app.game.classes import CLASS_STATS
        
        warrior_hp = CLASS_STATS["warrior"]["base_hp"]
        mage_hp = CLASS_STATS["mage"]["base_hp"]
        druid_hp = CLASS_STATS["druid"]["base_hp"]
        
        # Warrior should have highest HP
        assert warrior_hp > mage_hp, "Warrior should have more HP than Mage"
        assert warrior_hp > druid_hp, "Warrior should have more HP than Druid"
        
        # Mage should have lowest HP
        assert mage_hp < warrior_hp, "Mage should have less HP than Warrior"
        assert mage_hp < druid_hp, "Mage should have less HP than Druid"
        
        # Druid should be in between
        assert druid_hp > mage_hp, "Druid should have more HP than Mage"
        assert druid_hp < warrior_hp, "Druid should have less HP than Warrior"
        
        # HP values should be in reasonable ranges (70-140)
        assert 70 <= warrior_hp <= 140, "Warrior HP should be in reasonable range"
        assert 70 <= mage_hp <= 140, "Mage HP should be in reasonable range"
        assert 70 <= druid_hp <= 140, "Druid HP should be in reasonable range"
    
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
