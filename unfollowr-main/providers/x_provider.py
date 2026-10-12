"""
X (Twitter) unfollower detection.

Uses the X API v2 (requires at least Basic-tier paid API access — the free
tier does not expose the followers endpoint at usable volume) to fetch your
current follower list, then diffs it against the last saved snapshot to
find who unfollowed you since the previous run. Can also unfollow those
accounts back. Everything runs as the account signed in via auth.py.
"""

from datetime import datetime, timezone

import tweepy

from .. import auth, unfollower_list
from ..config import config
from ..snapshot import load_snapshot, save_snapshot

PLATFORM = "x"


def _fetch_followers(client: tweepy.Client, user_id: str) -> dict:
    """Return {user_id: username} for all current followers."""
    followers = {}
    for response in tweepy.Paginator(
        client.get_users_followers,
        id=user_id,
        max_results=1000,
        user_fields=["username"],
        user_auth=True,
    ):
        if response.data:
            for user in response.data:
                followers[str(user.id)] = user.username
    return followers


def run(login: dict) -> dict:
    """
    Fetch the signed-in account's current followers, diff against the previous snapshot, and return
    a result dict:
        {
            "platform": "x",
            "first_run": bool,
            "follower_count": int,
            "unfollowers": [ {"user_id", "username", "detected_at"}, ... ],
            "saved_unfollowers": [ ...same shape, all still on the saved list... ],
            "sheet_rows": [ [timestamp, user_id, username], ... ],
        }
    """
    client = auth.get_client(login)
    user_id = login["user_id"]
    account_dir = config.account_dir(user_id)

    current_followers = _fetch_followers(client, user_id)
    previous_followers = load_snapshot(account_dir, PLATFORM) or {}

    first_run = not previous_followers
    unfollower_ids = [] if first_run else [
        uid for uid in previous_followers if uid not in current_followers
    ]

    timestamp = datetime.now(timezone.utc).isoformat()
    unfollowers = [
        {"user_id": uid, "username": previous_followers.get(uid, "unknown"),
         "detected_at": timestamp}
        for uid in unfollower_ids
    ]
    sheet_rows = [[timestamp, u["user_id"], u["username"]] for u in unfollowers]

    save_snapshot(account_dir, PLATFORM, current_followers)
    saved_unfollowers = unfollower_list.update(user_id, unfollowers, current_followers)

    return {
        "platform": PLATFORM,
        "first_run": first_run,
        "follower_count": len(current_followers),
        "unfollowers": unfollowers,
        "saved_unfollowers": saved_unfollowers,
        "sheet_rows": sheet_rows,
    }


def unfollow(client: tweepy.Client, user_id: str) -> None:
    """Unfollow one account. Succeeds silently if you weren't following them."""
    client.unfollow_user(user_id)
