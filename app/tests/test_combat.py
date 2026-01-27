import pytest

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
from app.db.models import Match


def make_match():
    match = Match(
        player1_id=1,
        player2_id=2,
        status="active",
    )
    initialize_match(match)
    return match


class TestAttacks:
    def test_attack_reduces_health(self):
        match = make_match()

        result = process_attack(
            match=match,
            attacker_id=1,
            defender_id=2,
        )

        assert result["action"] == "attack"
        assert match.player2_health < 100


class TestDefense:
    def test_defend_reduces_damage(self):
        match = make_match()

        process_defend(match, player_id=2)
        before = match.player2_health

        process_attack(match, attacker_id=1, defender_id=2)

        after = match.player2_health
        assert before - after <= 10  # reduced damage


class TestHealing:
    def test_heal_caps_at_100(self):
        match = make_match()
        match.player1_health = 95

        result = process_heal(match, player_id=1)

        assert result["new_health"] == 100


class TestMatchEnd:
    def test_match_ends_when_health_zero(self):
        match = make_match()
        match.player2_health = 1

        process_attack(match, attacker_id=1, defender_id=2)
        winner = check_match_end(match)

        assert winner == 1
        assert match.status == "finished"


class TestTurns:
    def test_turn_switches_after_an_action(self):
        match = make_match()
        engine = CombatEngine()

        start_turn = match.current_turn

        # Do a valid action by the current player via the engine (auto-advances turn)
        if start_turn == match.player1_id:
            engine.attack(match, attacker_id=match.player1_id, defender_id=match.player2_id)
        else:
            engine.attack(match, attacker_id=match.player2_id, defender_id=match.player1_id)

        assert match.current_turn != start_turn

    def test_cannot_act_when_match_is_over(self):
        match = make_match()
        match.status = "finished"

        with pytest.raises(MatchNotActiveError):
            process_attack(match, attacker_id=1, defender_id=2)

    def test_wrong_player_cannot_act(self):
        match = make_match()
        engine = CombatEngine()

        # At start, it's player1's turn; player2 should not be able to act
        assert match.current_turn == match.player1_id

        with pytest.raises(InvalidActionError):
            engine.attack(match, attacker_id=match.player2_id, defender_id=match.player1_id)

    def test_player_cannot_act_twice_in_a_row(self):
        match = make_match()
        engine = CombatEngine()

        start_turn = match.current_turn
        opponent_id = match.player2_id if start_turn == match.player1_id else match.player1_id

        # First action is valid
        engine.attack(match, attacker_id=start_turn, defender_id=opponent_id)
        assert match.current_turn == opponent_id

        # Same player tries to act again immediately
        with pytest.raises(InvalidActionError):
            engine.attack(match, attacker_id=start_turn, defender_id=opponent_id)

    def test_dead_player_cannot_act(self):
        match = make_match()
        engine = CombatEngine()

        # Kill player2
        match.player2_health = 0

        with pytest.raises(InvalidActionError):
            engine.attack(match, attacker_id=match.player2_id, defender_id=match.player1_id)
