import re
from pathlib import Path

_PROFANITY_LOADED = False
_BANNED_ROOTS: list[str] = []

_LEET = str.maketrans("013457@$", "oieastas")


def _load_profanity_once() -> None:
    global _PROFANITY_LOADED
    if _PROFANITY_LOADED:
        return
    from better_profanity import profanity
    profanity.load_censor_words()
    _PROFANITY_LOADED = True


def _load_banned_roots() -> list[str]:
    global _BANNED_ROOTS
    if _BANNED_ROOTS:
        return _BANNED_ROOTS
    path = Path(__file__).resolve().parent / "banned_roots.txt"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            _BANNED_ROOTS = [line.strip().lower() for line in f if line.strip()]
    return _BANNED_ROOTS


def normalize_username(value: str) -> str:
    s = value.strip().lower()
    s = s.translate(_LEET)
    s = re.sub(r"[^a-z0-9]", "", s)
    return s


def is_disallowed_username(username: str) -> bool:
    _load_profanity_once()
    normalized = normalize_username(username)
    roots = _load_banned_roots()
    for root in roots:
        if len(root) < 3:
            continue
        if root in normalized:
            return True
    from better_profanity import profanity
    return profanity.contains_profanity(username)
