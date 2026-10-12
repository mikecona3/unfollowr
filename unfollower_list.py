"""
Saved list of X accounts that unfollowed you and haven't been dealt with yet
(unfollowed back or removed from the list). Persists between checks so
nothing is lost when a new check replaces the follower snapshot.
"""

import json
from pathlib import Path

from .config import config


def _path(account_id: str) -> Path:
    return config.account_dir(account_id) / "x_unfollowers.json"


def load(account_id: str) -> list:
    """Return an account's saved list as [{"user_id", "username", "detected_at"}, ...]."""
    path = _path(account_id)
    if path.exists():
        return json.loads(path.read_text())
    return []


def save(account_id: str, users: list) -> None:
    _path(account_id).write_text(json.dumps(users, indent=2))


def update(account_id: str, new_unfollowers: list, current_follower_ids) -> list:
    """Add new unfollowers, drop anyone who has followed you again, save, and return the list."""
    users = [u for u in load(account_id) if u["user_id"] not in current_follower_ids]
    known = {u["user_id"] for u in users}
    users += [u for u in new_unfollowers if u["user_id"] not in known]
    save(account_id, users)
    return users


def remove(account_id: str, user_ids) -> list:
    """Remove accounts from the saved list, save, and return what's left."""
    ids = set(user_ids)
    users = [u for u in load(account_id) if u["user_id"] not in ids]
    save(account_id, users)
    return users
