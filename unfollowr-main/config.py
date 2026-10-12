"""
Central configuration, loaded from environment variables (and, for the X
app keys, from x_app_keys.json next to this file).

All values are read at call time (not import time) so tests can monkeypatch
os.environ freely.
"""

import json
import os
from pathlib import Path

APP_KEYS_FILE = Path(__file__).parent / "x_app_keys.json"


class ConfigError(Exception):
    """Raised when required configuration is missing."""


class Config:
    # --- X app keys ---
    # These identify the app (from the developer's X account), not the user.
    # Users sign in with X from the app; their login is stored in data_dir.
    def _app_key(self, env_name: str, file_key: str) -> str:
        if os.environ.get(env_name):
            return os.environ[env_name]
        if APP_KEYS_FILE.exists():
            return json.loads(APP_KEYS_FILE.read_text()).get(file_key, "")
        return ""

    @property
    def x_api_key(self) -> str:
        return self._app_key("X_API_KEY", "api_key")

    @property
    def x_api_secret(self) -> str:
        return self._app_key("X_API_SECRET", "api_secret")

    # --- Google Sheets ---
    @property
    def google_service_account_file(self) -> str:
        return os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE", "service_account.json")

    @property
    def google_sheet_id(self) -> str:
        return os.environ.get("GOOGLE_SHEET_ID", "")

    @property
    def google_sheet_tab_x(self) -> str:
        return os.environ.get("GOOGLE_SHEET_TAB_X", "X Unfollowers")

    # --- Local storage (login, snapshots, saved unfollower lists) ---
    @property
    def data_dir(self) -> Path:
        path = Path(os.environ.get("UNFOLLOWR_DATA_DIR", Path.home() / ".unfollowr"))
        path.mkdir(parents=True, exist_ok=True)
        return path

    def account_dir(self, user_id: str) -> Path:
        """Per-account folder so switching accounts never mixes up follower data."""
        path = self.data_dir / user_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def require_app_keys(self) -> None:
        if not self.x_api_key or not self.x_api_secret:
            raise ConfigError(
                "The app's X API key and secret aren't set up. "
                f"Add them to {APP_KEYS_FILE.name} (see README)."
            )


config = Config()
