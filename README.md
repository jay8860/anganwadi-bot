# Anganwadi Bot

A Telegram bot to monitor Anganwadi workers' activities, track streaks, and generate daily performance reports.

## Features
- **Daily Reporting**: 2 PM status check and 6 PM final report.
- **Streak Tracking**: Tracks daily streaks for every worker.
- **Excel Export**: Generates a list of workers who missed their submission.
- **Timezone**: Configured for IST (Asia/Kolkata).

## How to Deploy (The Easy Way)

### Option 1: Railway (Recommended)
1.  Sign up at [railway.app](https://railway.app/).
2.  Click **New Project** > **Deploy from GitHub repo**.
3.  Select this repository (`anganwadi-bot`).
4.  Adding Variables:
    - Go to **Variables** tab.
    - Add `TELEGRAM_BOT_TOKEN` with your bot token.
5.  **Important (Persisting Data)**:
    - Go to **Volumes** tab.
    - Click **Add Volume**.
    - Mount path: `/app/anganwadi.db` (or just `/app` if using SQLite config directly).
    - *Note: Without this, streaks will reset every time the bot updates.*

### Option 2: Render
1.  Sign up at [render.com](https://render.com/).
2.  New **Web Service** (or Background Worker) > Connect GitHub.
3.  Runtime: **Docker**.
4.  Add Environment Variable: `TELEGRAM_BOT_TOKEN`.
5.  *Note: Free tier on Render spins down (sleeps), so the bot might be slow to wake up, and it does not support persistent disk for SQLite (data will be lost on restart).*

## Local Development
1.  Clone the repo.
2.  `pip install -r requirements.txt`
3.  Run `python main.py`
