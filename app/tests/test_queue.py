from app.game.engine import MatchmakingQueue


class TestMatchmakingQueue:
    def test_join_twice_does_not_duplicate(self):
        q = MatchmakingQueue()

        q.join(1)
        q.join(1)

        assert q.size() == 1
        assert q.position(1) == 1

    def test_pop_pair_requires_two_or_more(self):
        q = MatchmakingQueue()

        # With fewer than 2 players, no pair is returned
        q.join(1)
        assert q.pop_pair() is None

        # With 2 players, a pair is returned in FIFO order
        q.join(2)
        pair = q.pop_pair()

        assert pair == (1, 2)
        assert q.size() == 0

    def test_leave_removes_player(self):
        q = MatchmakingQueue()

        q.join(1)
        q.join(2)
        q.join(3)

        q.leave(2)

        assert q.size() == 2
        assert q.position(1) == 1
        assert q.position(2) is None
        assert q.position(3) == 2

    def test_leave_nonexistent_is_noop(self):
        q = MatchmakingQueue()

        q.join(1)
        q.leave(999)

        assert q.size() == 1
        assert q.position(1) == 1

    def test_pop_pair_preserves_order_for_remaining(self):
        q = MatchmakingQueue()

        q.join(1)
        q.join(2)
        q.join(3)

        pair = q.pop_pair()

        assert pair == (1, 2)
        assert q.size() == 1
        assert q.position(3) == 1


