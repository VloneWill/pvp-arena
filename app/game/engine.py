from collections import deque


class MatchmakingQueue:
    def __init__(self):
        self._q = deque()

    def join(self, user_id: int) -> None:
        if user_id in self._q:
            return
        self._q.append(user_id)

    def leave(self, user_id: int) -> None:
        try:
            self._q.remove(user_id)
        except ValueError:
            return

    def pop_pair(self) -> tuple[int, int] | None:
        if len(self._q) < 2:
            return None
        p1 = self._q.popleft()
        p2 = self._q.popleft()
        return (p1, p2)

    def position(self, user_id: int) -> int | None:
        try:
            return list(self._q).index(user_id) + 1
        except ValueError:
            return None

    def size(self) -> int:
        return len(self._q)


queue = MatchmakingQueue()
