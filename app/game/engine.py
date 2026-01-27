#imports for the matchmaking queue
from collections import deque


#create the matchmaking queue class
class MatchmakingQueue:
    #create the init method
    def __init__(self):
        self._q = deque()

    #create the join method
    def join(self, user_id: int) -> None:
        if user_id in self._q:
            return
        self._q.append(user_id)

    #create the leave method
    def leave(self, user_id: int) -> None:
        try:
            self._q.remove(user_id)
        except ValueError:
            return

    #create the pop pair method
    def pop_pair(self) -> tuple[int, int] | None:
        if len(self._q) < 2:
            return None
        p1 = self._q.popleft()
        p2 = self._q.popleft()
        return (p1, p2)

    #create the position method
    def position(self, user_id: int) -> int | None:
        try:
            return list(self._q).index(user_id) + 1
        except ValueError:
            return None

    #create the size method
    def size(self) -> int:
        return len(self._q)


#create the queue instance
queue = MatchmakingQueue()
