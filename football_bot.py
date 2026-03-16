import asyncio
import logging
import aiohttp
from datetime import datetime, date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes
)

# ── CONFIG ────────────────────────────────────────────────────────────────────
TELEGRAM_TOKEN   = "8652746799:AAECKIG4zR5Mhmh8KOSjMD-4ZjHhAEUAg8M"
FOOTBALL_API_KEY = "c7f5bf9257c7fcb543f8638fad4336d8"
FOOTBALL_API_URL = "https://v3.football.api-sports.io"

LEAGUES = {
    "🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League": 39,
    "🇪🇸 La Liga":         140,
    "🇩🇪 Bundesliga":      78,
    "🇮🇹 Serie A":         135,
    "🇫🇷 Ligue 1":         61,
    "🌍 Champions League": 2,
    "🌍 Europa League":    3,
    "🌍 AFCON":            6,
}

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ── API HELPERS ───────────────────────────────────────────────────────────────
async def api_get(endpoint: str, params: dict) -> dict:
    headers = {
        "x-apisports-key": FOOTBALL_API_KEY,
        "x-rapidapi-host": "v3.football.api-sports.io",
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{FOOTBALL_API_URL}/{endpoint}", headers=headers, params=params) as r:
            return await r.json()

def flag(country: str) -> str:
    flags = {
        "England": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "Spain": "🇪🇸", "Germany": "🇩🇪",
        "Italy": "🇮🇹", "France": "🇫🇷", "Portugal": "🇵🇹",
        "Netherlands": "🇳🇱", "Brazil": "🇧🇷", "Argentina": "🇦🇷",
    }
    return flags.get(country, "🌍")

# ── FORMAT HELPERS ────────────────────────────────────────────────────────────
def format_live_match(f: dict) -> str:
    home = f["teams"]["home"]
    away = f["teams"]["away"]
    score = f["score"]["fulltime"]
    goals = f["goals"]
    elapsed = f["fixture"]["status"]["elapsed"] or "?"
    status  = f["fixture"]["status"]["short"]

    hg = goals["home"] if goals["home"] is not None else 0
    ag = goals["away"] if goals["away"] is not None else 0

    if status == "HT":
        time_str = "⏸ HT"
    elif status == "FT":
        time_str = "✅ FT"
    elif status in ("1H", "2H", "ET"):
        time_str = f"🔴 {elapsed}'"
    else:
        time_str = status

    return (
        f"⚽ *{home['name']}* {hg} - {ag} *{away['name']}*\n"
        f"   {time_str}  |  {f['league']['name']}"
    )

def format_summary(f: dict) -> str:
    home = f["teams"]["home"]
    away = f["teams"]["away"]
    goals = f["goals"]
    hg = goals["home"] if goals["home"] is not None else 0
    ag = goals["away"] if goals["away"] is not None else 0
    winner = home["name"] if hg > ag else (away["name"] if ag > hg else "Draw")
    result_emoji = "🏆" if winner != "Draw" else "🤝"

    lines = [
        f"━━━━━━━━━━━━━━━━━━━━",
        f"📋 *MATCH SUMMARY*",
        f"━━━━━━━━━━━━━━━━━━━━",
        f"🏟 {f['league']['name']} | {f['league']['round']}",
        f"",
        f"*{home['name']}* {hg} — {ag} *{away['name']}*",
        f"",
        f"{result_emoji} Result: *{'Draw' if winner == 'Draw' else winner + ' Win'}*",
    ]
    return "\n".join(lines)

def format_whatsapp_caption(f: dict) -> str:
    home = f["teams"]["home"]
    away = f["teams"]["away"]
    goals = f["goals"]
    hg = goals["home"] if goals["home"] is not None else 0
    ag = goals["away"] if goals["away"] is not None else 0
    league = f["league"]["name"]
    round_ = f["league"].get("round", "")
    winner = home["name"] if hg > ag else (away["name"] if ag > hg else None)

    if winner:
        headline = f"🚨 {winner.upper()} WIN! 🚨"
    else:
        headline = "🤝 IT ENDS ALL SQUARE!"

    caption = (
        f"{headline}\n\n"
        f"⚽ {home['name']} {hg} - {ag} {away['name']}\n\n"
        f"🏆 {league}\n"
        f"📅 {round_}\n\n"
        f"Follow for more football updates! 🔔\n"
        f"#Football #{league.replace(' ', '')} #{home['name'].replace(' ', '')} #{away['name'].replace(' ', '')}"
    )
    return caption

def format_fixture(f: dict) -> str:
    home = f["teams"]["home"]["name"]
    away = f["teams"]["away"]["name"]
    dt   = datetime.fromisoformat(f["fixture"]["date"].replace("Z", "+00:00"))
    time_str = dt.strftime("%a %d %b, %H:%M UTC")
    venue = f["fixture"].get("venue", {}).get("name", "TBC")
    return f"📅 *{home}* vs *{away}*\n   🕐 {time_str}\n   🏟 {venue}"

# ── KEYBOARDS ─────────────────────────────────────────────────────────────────
def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔴 Live Scores",       callback_data="live")],
        [InlineKeyboardButton("📋 Match Summaries",   callback_data="summaries")],
        [InlineKeyboardButton("📣 WhatsApp Captions", callback_data="captions")],
        [InlineKeyboardButton("📅 Today's Fixtures",  callback_data="fixtures")],
    ])

def league_keyboard(action: str):
    rows = []
    for name, lid in LEAGUES.items():
        rows.append([InlineKeyboardButton(name, callback_data=f"{action}_{lid}")])
    rows.append([InlineKeyboardButton("🔙 Back", callback_data="back")])
    return InlineKeyboardMarkup(rows)

# ── HANDLERS ──────────────────────────────────────────────────────────────────
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = (
        "👋 Welcome to your *Football Updates Bot*!\n\n"
        "I'll help you get the latest scores, summaries, and ready-made captions "
        "for your WhatsApp channel. What would you like? 👇"
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=main_menu_keyboard())

async def help_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Commands:*\n"
        "/start — Main menu\n"
        "/live — Live scores\n"
        "/fixtures — Today's fixtures\n"
        "/summaries — Recent results\n"
        "/captions — WhatsApp captions\n"
        "/help — This message",
        parse_mode="Markdown"
    )

async def button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "back":
        await query.edit_message_text(
            "🏠 *Main Menu* — What would you like?",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )

    elif data == "live":
        await query.edit_message_text("⏳ Fetching live matches…")
        data2 = await api_get("fixtures", {"live": "all"})
        fixtures = data2.get("response", [])
        if not fixtures:
            await query.edit_message_text(
                "😴 No live matches right now.\n\nCheck back when games are on!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="back")]])
            )
            return
        lines = ["🔴 *LIVE SCORES*\n"]
        for f in fixtures[:15]:
            lines.append(format_live_match(f))
        lines.append("\n_Tap 🔄 to refresh_")
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Refresh", callback_data="live")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ])
        await query.edit_message_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb)

    elif data == "summaries":
        await query.edit_message_text("Choose a league:", reply_markup=league_keyboard("sum"))

    elif data == "captions":
        await query.edit_message_text("Choose a league for captions:", reply_markup=league_keyboard("cap"))

    elif data == "fixtures":
        await query.edit_message_text("Choose a league for fixtures:", reply_markup=league_keyboard("fix"))

    elif data.startswith("sum_"):
        league_id = int(data.split("_")[1])
        await query.edit_message_text("⏳ Fetching recent results…")
        today = date.today().isoformat()
        data2 = await api_get("fixtures", {"league": league_id, "season": 2024, "status": "FT", "last": 5})
        fixtures = data2.get("response", [])
        if not fixtures:
            await query.edit_message_text(
                "No recent results found for this league.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="summaries")]])
            )
            return
        lines = ["📋 *RECENT RESULTS*\n"]
        for f in fixtures:
            home = f["teams"]["home"]["name"]
            away = f["teams"]["away"]["name"]
            hg = f["goals"]["home"] or 0
            ag = f["goals"]["away"] or 0
            lines.append(f"✅ *{home}* {hg} - {ag} *{away}*")
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="summaries")]])
        await query.edit_message_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb)

    elif data.startswith("cap_"):
        league_id = int(data.split("_")[1])
        await query.edit_message_text("⏳ Generating captions…")
        data2 = await api_get("fixtures", {"league": league_id, "season": 2024, "status": "FT", "last": 5})
        fixtures = data2.get("response", [])
        if not fixtures:
            await query.edit_message_text(
                "No recent results to generate captions from.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="captions")]])
            )
            return
        for f in fixtures[:3]:
            caption = format_whatsapp_caption(f)
            await query.message.reply_text(
                f"📣 *Copy this to WhatsApp:*\n\n{caption}",
                parse_mode="Markdown"
            )
        await query.edit_message_text(
            "✅ Captions sent above — copy & paste to your WhatsApp channel!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="captions")]])
        )

    elif data.startswith("fix_"):
        league_id = int(data.split("_")[1])
        await query.edit_message_text("⏳ Fetching fixtures…")
        data2 = await api_get("fixtures", {"league": league_id, "season": 2024, "next": 5})
        fixtures = data2.get("response", [])
        if not fixtures:
            await query.edit_message_text(
                "No upcoming fixtures found.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="fixtures")]])
            )
            return
        lines = ["📅 *UPCOMING FIXTURES*\n"]
        for f in fixtures:
            lines.append(format_fixture(f))
            lines.append("")
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="fixtures")]])
        await query.edit_message_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb)

# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start",     start))
    app.add_handler(CommandHandler("help",      help_cmd))
    app.add_handler(CommandHandler("live",      lambda u, c: button(u, c)))
    app.add_handler(CallbackQueryHandler(button))
    logger.info("⚽ Football Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
