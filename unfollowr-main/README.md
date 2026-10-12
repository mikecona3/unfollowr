# Unfollower Tracker

Tracks who unfollows you on X (Twitter), and lets you unfollow them back
from a simple desktop app.

## How it works

Each check:

1. Fetches the signed-in account's current follower list from the
   official X API.
2. Compares it to a local JSON snapshot saved from the previous check
   (`x_snapshot.json`).
3. Anyone in the old snapshot but missing now is logged as an unfollower.
4. Appends new unfollowers to a Google Sheet, or prints them if Sheets
   isn't configured.
5. Saves the current follower list as the new snapshot.

**The first check only establishes a baseline.** Unfollowers start showing
up from the second check.

## Requirements

- Python 3.9+
- An X developer account with at least **Basic-tier** API access
  (the free tier doesn't expose the followers endpoint at usable limits).
  Only whoever sets the app up needs this. People using the app just sign
  in with their normal X account.
- **For Sheets export** (optional): a Google Cloud service account with the
  Sheets and Drive APIs enabled.

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. X app keys (one-time, by whoever sets the app up)

1. Create a project/app at [developer.x.com](https://developer.x.com).
2. In the app's **User authentication settings**:
   - App permissions: **Read and write**
   - Type of app: **Native App**
   - Callback URI / Website URL: any valid URL (e.g. your website). The app
     signs in with a PIN, so the callback isn't used.
3. Under **Keys and tokens**, copy the **API Key** and **API Key Secret**
   into `x_app_keys.json` next to the code:

   ```json
   {
     "api_key": "your-api-key",
     "api_secret": "your-api-key-secret"
   }
   ```

   These identify the app, not any user. Don't publish this file (it's
   listed in `.gitignore`). `X_API_KEY` / `X_API_SECRET` environment
   variables override it if set.

### 3. Google Sheets credentials (optional)

1. Create a service account in [Google Cloud Console](https://console.cloud.google.com/).
2. Enable the **Google Sheets API** and **Google Drive API**.
3. Download the service account's JSON key.
4. Share your target Google Sheet with the service account's email
   (the `client_email` field in the JSON key), with Editor access.
5. Copy the spreadsheet ID from its URL:
   `https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit`

### 4. Optional environment variables

```bash
# Google Sheets — omit to just print results instead
# export GOOGLE_SERVICE_ACCOUNT_FILE="/path/to/service_account.json"
# export GOOGLE_SHEET_ID="your-spreadsheet-id"
# export GOOGLE_SHEET_TAB_X="X Unfollowers"   # optional

# Where the login, snapshots and saved lists are stored (default: ~/.unfollowr)
# export UNFOLLOWR_DATA_DIR="/path/to/data"
```

## Usage

### Desktop app

```bash
python -m unfollower_tracker.gui
```

1. Press **Sign in with X**. X's login page opens in your browser. Log in
   there (the app never sees your password) and click **Authorize app**.
2. X shows a PIN. Type it into the app.
3. Press **Find Unfollowers on X**.

The login is saved, so you stay signed in next time you open the app. Use
**Sign Out** to disconnect or switch accounts. Each account keeps its own
snapshot and saved list in `~/.unfollowr/<account id>/`.

Unfollowers are kept on a saved list (`x_unfollowers.json`). It loads when
the app opens, and each check adds new unfollowers to it. Anyone who
follows you again drops off automatically.
Select accounts (or **Select All**), then either:

- **Unfollow Selected**: unfollows them on X and removes them from the list.
  The app asks for confirmation first.
- **Remove from List**: removes them from the list without unfollowing.

X allows about 50 unfollows per 15 minutes. Past that, the app pauses
until the limit resets.

### Command line

```bash
python -m unfollower_tracker
```

Runs one check for the account signed in through the app and prints the
results. Handy for scheduling with cron.

## Notes & limitations

- X API rate limits apply for large follower counts; `wait_on_rate_limit=True`
  handles this automatically but large accounts may take a while.
- Changes are only detected between checks — someone who follows and
  unfollows between two checks won't be caught.

## License

MIT — do whatever you want with it.
