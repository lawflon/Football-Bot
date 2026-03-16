import logging
import requests
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ── CONFIG ────────────────────────────────────────────────────────────────────
TELEGRAM_TOKEN   = "8652746799:AAECKIG4zR5Mhmh8KOSjMD-4ZjHhAEUAg8M"
FOOTBALL_API_KEY = "c7f5bf9257c7fcb543f8638fad4336d8"
FOOTBALL_API_URL = "https://v3.football.api-sports.io"

LEAGUES = {
    "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League": 39,
    "🇪🇸 La Liga": 140,
    "🇩🇪 Bundesliga": 78,
    "🇮🇹 Serie A": 135,
    "🇫🇷 Ligue 1": 61,
    "🌍 Champions League": 2,
    "🌍 Europa League": 3,
    "🌍 AFCON": 6,
}

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

def api_get(endpoint, params):
    headers = {"x-apisports-key": FOOTBALL_API_KEY}
    try:
        r = requests.get(f"{FOOTBALL_API_URL}/{endpoint}", headers=headers, params=params, timeout=10)
        return r.json()
    except Exception as e:
        logger.error(f"API error: {e}")
        return {"response": []}

def format_live_match(f):
    home = f["teams"]["home"]["name"]
    away = f["teams"]["away"]["name"]
    hg = f["goals"]["home"] if f["goals"]["home"] is not None else 0
    ag = f["goals"]["away"] if f["goals"]["away"] is not None else 0
    elapsed = f["fixture"]["status"]["elapsed"] or "?"
    status = f["fixture"]["status"]["short"]
    if status == "HT": time_str = "⏸ HT"
    elif status == "FT": time_str = "✅ FT"
    elif status in ("1H", "2H", "ET"): time_str = f"🔴 {elapsed}'"
    else: time_str = status
    return f"⚽ *{home}* {hg} - {ag} *{away}*\n   {time_str}  |  {f['league']['name']}"

def format_result(f):
    home = f["teams"]["home"]["name"]
    away = f["teams"]["away"]["name"]
    hg = f["goals"]["home"] if f["goals"]["home"] is not None else 0
    ag = f["goals"]["away"] if f["goals"]["away"] is not None else 0
    return f"✅ *{home}* {hg} - {ag} *{away}*"

def format_fixture(f):
    home = f["teams"]["home"]["name"]
    away = f["teams"]["away"]["name"]
    dt = datetime.fromisoformat(f["fixture"]["date"].replace("Z", "+00:00"))
    time_str = dt.strftime("%a %d %b, %H:%M UTC")
    venue = f["fixture"].get("venue", {}).get("name", "TBC")
    return f"📅 *{home}* vs *{away}*\n   🕐 {time_str}\n   🏟 {venue}"

def format_caption(f):
    home = f["teams"]["home"]["name"]
    away = f["teams"]["away"]["name"]
    hg = f["goals"]["home"] if f["goals"]["home"] is not None else 0
    ag = f["goals"]["away"] if f["goals"]["away"] is not None else 0
    league = f["league"]["name"]
    round_ = f["league"].get("round", "")
    winner = home if hg > ag else (away if ag > hg else None)
    headline = f"🚨 {winner.upper()} WIN! 🚨" if winner else "🤝 IT ENDS ALL SQUARE!"
    return (
        f"{headline}\n\n"
        f"⚽ {home} {hg} - {ag} {away}\n\n"
        f"🏆 {league}\n📅 {round_}\n\n"
        f"Follow for more football updates! 🔔\n"
        f"#Football #{league.replace(' ','')} #{home.replace(' ','')} #{away.replace(' ','')}"
    )

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔴 Live Scores", callback_data="live")],
        [InlineKeyboardButton("📋 Match Summaries", callback_data="summaries")],
        [InlineKeyboardButton("📣 WhatsApp Captions", callback_data="captions")],
        [InlineKeyboardButton("📅 Fixtures", callback_data="fixtures")],
    ])

def league_kb(action):
    rows = [[InlineKeyboardButton(n, callback_data=f"{action}_{lid}")] for n, lid in LEAGUES.items()]
    rows.append([InlineKeyboardButton("🔙 Back", callback_data="back")])
    return InlineKeyboardMarkup(rows)

def back_kb(target):
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data=target)]])

async def start(update, ctx):
    await update.message.reply_text(
        "👋 Welcome to your *Football Updates Bot*!\n\nGet live scores, results & WhatsApp captions. 👇",
        parse_mode="Markdown", reply_markup=main_menu()
    )

async def button(update, ctx):
    q = update.callback_query
    await q.answer()
    d = q.data

    if d == "back":
        await q.edit_message_text("🏠 *Main Menu*", parse_mode="Markdown", reply_markup=main_menu())

    elif d == "live":
        await q.edit_message_text("⏳ Fetching live matches…")
        fx = api_get("fixtures", {"live": "all"}).get("response", [])
        if not fx:
            await q.edit_message_text("😴 No live matches right now!", reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Refresh", callback_data="live")],
                [InlineKeyboardButton("🔙 Back", callback_data="back")]
            ]))
            return
        lines = ["🔴 *LIVE SCORES*\n"] + [format_live_match(f) for f in fx[:15]]
        await q.edit_message_text("\n".join(lines), parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Refresh", callback_data="live")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]))

    elif d == "summaries":
        await q.edit_message_text("Choose a league:", reply_markup=league_kb("sum"))

    elif d.startswith("sum_"):
        lid = int(d.split("_")[1])
        await q.edit_message_text("⏳ Fetching results…")
        fx = api_get("fixtures", {"league": lid, "season": 2024, "status": "FT", "last": 5}).get("response", [])
        if not fx:
            await q.edit_message_text("No recent results found.", reply_markup=back_kb("summaries"))
            return
        lines = ["📋 *RECENT RESULTS*\n"] + [format_result(f) for f in fx]
        await q.edit_message_text("\n".join(lines), parse_mode="Markdown", reply_markup=back_kb("summaries"))

    elif d == "captions":
        await q.edit_message_text("Choose a league:", reply_markup=league_kb("cap"))

    elif d.startswith("cap_"):
        lid = int(d.split("_")[1])
        await q.edit_message_text("⏳ Generating captions…")
        fx = api_get("fixtures", {"league": lid, "season": 2024, "status": "FT", "last": 3}).get("response", [])
        if not fx:
            await q.edit_message_text("No recent results found.", reply_markup=back_kb("captions"))
            return
        for f in fx:
            await q.message.reply_text(f"📣 *Copy this to WhatsApp:*\n\n{format_caption(f)}", parse_mode="Markdown")
        await q.edit_message_text("✅ Captions ready above!", reply_markup=back_kb("captions"))

    elif d == "fixtures":
        await q.edit_message_text("Choose a league:", reply_markup=league_kb("fix"))

    elif d.startswith("fix_"):
        lid = int(d.split("_")[1])
        await q.edit_message_text("⏳ Fetching fixtures…")
        fx = api_get("fixtures", {"league": lid, "season": 2024, "next": 5}).get("response", [])
        if not fx:
            await q.edit_message_text("No upcoming fixtures found.", reply_markup=back_kb("fixtures"))
            return
        lines = ["📅 *UPCOMING FIXTURES*\n"]
        for f in fx:
            lines.append(format_fixture(f))
            lines.append("")
        await q.edit_message_text("\n".join(lines), parse_mode="Markdown", reply_markup=back_kb("fixtures"))

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    logger.info("⚽ Football Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
