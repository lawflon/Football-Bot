# ⚽ Football Updates Bot — Setup Guide

## What You Need
- A PC or VPS running Python 3.10+
- Your Telegram Bot Token ✅ (already in bot)
- Your API-Football Key ✅ (already in bot)

---

## 🚀 How to Run the Bot

### Step 1 — Install Python
Download from https://python.org if you don't have it.

### Step 2 — Install dependencies
Open a terminal/command prompt in the folder where you saved the files, then run:

```
pip install -r requirements.txt
```

### Step 3 — Run the bot
```
python football_bot.py
```

You'll see: `⚽ Football Bot is running...`

---

## 📱 How to Use the Bot

1. Open Telegram and search for your bot (the name you gave BotFather)
2. Send `/start`
3. Choose from the menu:
   - 🔴 **Live Scores** — See all live matches right now
   - 📋 **Match Summaries** — Recent results by league
   - 📣 **WhatsApp Captions** — Pre-written posts ready to copy
   - 📅 **Today's Fixtures** — Upcoming matches by league

---

## 🔁 Keep it Running 24/7 (Optional)

To keep the bot running even after you close your laptop, deploy it free on:
- **Railway.app** — easiest, free tier available
- **Render.com** — also free
- **PythonAnywhere.com** — free for basic bots

Just upload both files (`football_bot.py` + `requirements.txt`) and click Deploy.

---

## ❓ Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` again |
| Bot not responding | Make sure the script is still running |
| No live scores showing | There may be no games on right now |
| API errors | Check your API-Football key is correct |
