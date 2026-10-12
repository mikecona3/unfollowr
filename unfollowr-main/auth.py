"""
"Sign in with X" using X's PIN-based OAuth flow, plus the saved login.

The user logs in on X's own website and pastes back a PIN, so the app never
sees their password. The resulting login is saved (readable only by the
current user) so they stay signed in between launches.
"""

import json
import os
from typing import Optional

from .config import config


def _login_path():
    return config.data_dir / "login.json"


def start_sign_in():
    """Begin sign-in. Returns (handler, url): open url in a browser, then pass the PIN to finish_sign_in."""
    import tweepy

    config.require_app_keys()
    handler = tweepy.OAuth1UserHandler(config.x_api_key, config.x_api_secret, callback="oob")
    return handler, handler.get_authorization_url()


def finish_sign_in(handler, pin: str) -> dict:
    """Exchange the PIN for a login, save it, and return it."""
    import tweepy

    token, secret = handler.get_access_token(pin.strip())
    client = tweepy.Client(
        consumer_key=config.x_api_key, consumer_secret=config.x_api_secret,
        access_token=token, access_token_secret=secret,
    )
    me = client.get_me(user_auth=True).data
    login = {
        "user_id": str(me.id),
        "username": me.username,
        "access_token": token,
        "access_token_secret": secret,
    }
    save_login(login)
    return login


def load_login() -> Optional[dict]:
    path = _login_path()
    if path.exists():
        return json.loads(path.read_text())
    return None


def save_login(login: dict) -> None:
    path = _login_path()
    # Owner-only permissions: these tokens can act as the user's account
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(login, f, indent=2)


def sign_out() -> None:
    _login_path().unlink(missing_ok=True)


def get_client(login: dict):
    """API client acting as the signed-in user."""
    import tweepy

    config.require_app_keys()
    return tweepy.Client(
        consumer_key=config.x_api_key, consumer_secret=config.x_api_secret,
        access_token=login["access_token"], access_token_secret=login["access_token_secret"],
        wait_on_rate_limit=True,
    )
