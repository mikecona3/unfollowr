#!/usr/bin/env python3
"""
Unfollower Tracker
==================
Tracks who unfollows you on X. See README.md for full setup instructions.

Usage:
    python -m unfollower_tracker        # command line
    python -m unfollower_tracker.gui    # desktop app
"""

import argparse
import sys

from . import auth, unfollower_list
from .config import ConfigError
from .sheets_export import export_x_rows


def run_x(login: dict) -> list:
    """
    Check the signed-in account for unfollowers. Returns the full saved
    unfollower list (new ones plus any left over from earlier checks) as
    [{"user_id", "username", ...}].
    """
    from .providers import x_provider

    print(f"=== X (@{login['username']}) ===")
    try:
        result = x_provider.run(login)
    except ConfigError as e:
        print(f"Can't check X: {e}")
        return unfollower_list.load(login["user_id"])

    print(f"Current followers: {result['follower_count']}")
    if result["first_run"]:
        print("No previous snapshot found — baseline saved. "
              "Run again later to detect unfollowers.")
    elif not result["unfollowers"]:
        print("No new unfollowers since last run.")
    else:
        print(f"Detected {len(result['unfollowers'])} new unfollower(s):")
        for u in result["unfollowers"]:
            print(f"  - @{u['username']} (id: {u['user_id']})")
        export_x_rows(result["sheet_rows"])

    saved = result["saved_unfollowers"]
    if saved:
        print(f"{len(saved)} account(s) on your saved unfollower list.")
    return saved


def unfollow_x(login: dict, users: list) -> list:
    """Unfollow each user from the signed-in account. Returns the ones successfully unfollowed."""
    import tweepy
    from .providers import x_provider

    try:
        client = auth.get_client(login)
    except ConfigError as e:
        print(f"Can't unfollow: {e}")
        return []

    if len(users) > 50:
        print("X allows about 50 unfollows per 15 minutes — "
              "this will pause automatically when the limit is hit.")

    done = []
    for u in users:
        try:
            x_provider.unfollow(client, u["user_id"])
        except tweepy.TweepyException as e:
            print(f"  Could not unfollow @{u['username']}: {e}")
            continue
        print(f"  Unfollowed @{u['username']}")
        done.append(u)
    unfollower_list.remove(login["user_id"], (u["user_id"] for u in done))
    print(f"Unfollowed {len(done)} of {len(users)} account(s).")
    return done


def main() -> None:
    argparse.ArgumentParser(description="Track unfollowers on X.").parse_args()
    login = auth.load_login()
    if not login:
        print("Not signed in. Open the app (python -m unfollower_tracker.gui) "
              "and use Sign in with X first.")
        sys.exit(1)
    run_x(login)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # top-level safety net so cron jobs log a clear error
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)
