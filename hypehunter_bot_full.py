import nest_asyncio
import pytz
import pytz
import pytz
import pytz
import logging
import asyncio
from datetime import datetime
from functools import wraps

import requests
import nest_asyncio
nest_asyncio.apply()
import json
import pytz

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("start", start))


)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# --- Constants and API keys (embedded) ---
import os
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
HF_API_KEY = "YOUR_HUGGINGFACE_API_KEY_HERE"
# Admin user IDs (replace with actual IDs)
ADMIN_IDS = [123456789]

# Bot reference for scheduled tasks
bot = None

# --- Global storage for demonstration (replace with database in production) ---
users_data = {}  # user_id: {'gdpr': bool, 'portfolio': {symbol: amount}, 'role': 'user'}

# Logging setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Cache for coin list
COIN_LIST = None

def get_coin_id(symbol):
    """Get Coingecko coin ID from symbol."""
    global COIN_LIST
    if COIN_LIST is None:
        try:
            res = requests.get("https://api.coingecko.com/api/v3/coins/list")
            res.raise_for_status()
            COIN_LIST = res.json()
        except Exception as e:
            return None
    for coin in COIN_LIST:
        if coin["symbol"].upper() == symbol.upper():
            return coin["id"]
    return None

# --- Decorators ---
def admin_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id not in ADMIN_IDS:
            await update.message.reply_text("🚫 Du bist nicht berechtigt, diesen Befehl zu verwenden.")
            return
        return await func(update, context)
    return wrapper

# --- GDPR Consent ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start: greet user and ask for GDPR consent if new."""
    user_id = update.effective_user.id
    if user_id not in users_data:
        users_data[user_id] = {"gdpr": False, "portfolio": {}, "role": "user"}
    if not users_data[user_id]["gdpr"]:
        keyboard = [
            [
                InlineKeyboardButton("✅ Ich stimme zu", callback_data="GDPR_ACCEPT"),
                InlineKeyboardButton("❌ Ablehnen", callback_data="GDPR_DECLINE"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Bitte stimme unserer Datenschutzerklärung zu, um fortzufahren.",
            reply_markup=reply_markup,
        )
    else:
        await show_main_menu(update, context)

async def gdpr_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback query handler for GDPR consent."""
    query = update.callback_query
    await query.answer()
    choice = query.data
    user_id = query.from_user.id
    if choice == "GDPR_ACCEPT":
        users_data[user_id]["gdpr"] = True
        await query.edit_message_text(
            "✅ Vielen Dank! Du hast der Datenschutzerklärung zugestimmt. Du kannst den Bot nun verwenden."
        )
        await show_main_menu(update, context)
    elif choice == "GDPR_DECLINE":
        await query.edit_message_text(
            "❗ Du musst der Datenschutzerklärung zustimmen, um den Bot zu verwenden."
        )

# --- Main Menu ---
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display the main menu with inline buttons."""
    keyboard = [
        [InlineKeyboardButton("1️⃣ Top 5 Report", callback_data="TOP5")],
        [InlineKeyboardButton("2️⃣ Technische Analyse (RSI)", callback_data="TECH_ANALYSIS")],
        [InlineKeyboardButton("3️⃣ Social Buzz", callback_data="SOCIAL_BUZZ")],
        [InlineKeyboardButton("4️⃣ HypeHunter Einschätzung (KI)", callback_data="GPT_ANALYSIS")],
        [InlineKeyboardButton("5️⃣ Fundamental Daten", callback_data="FUNDAMENTAL")],
        [InlineKeyboardButton("❌ Beenden", callback_data="EXIT")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await update.callback_query.edit_message_text("Was möchtest du tun?", reply_markup=reply_markup)
    else:
        await update.message.reply_text("**Willkommen beim HypeHunterBot!**\nBitte wähle eine Option:", reply_markup=reply_markup, parse_mode="Markdown")

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle selection from main menu via callback queries."""
    query = update.callback_query
    await query.answer()
    data = query.data
    logger.info(f"User {query.from_user.id} selected {data}")
    if data == "TOP5":
        await generate_top5_report(query, context)
    elif data == "TECH_ANALYSIS":
        context.user_data["rsi_mode"] = True
        await query.edit_message_text("Bitte gib das Symbol der Kryptowährung für die RSI-Berechnung ein (z.B. BTC).")
    elif data == "SOCIAL_BUZZ":
        await social_buzz_analysis(query, context)
    elif data == "GPT_ANALYSIS":
        await gpt_analysis(query, context)
    elif data == "FUNDAMENTAL":
        await fundamental_data(query, context)
    elif data == "EXIT":
        await query.edit_message_text("Bot wurde beendet. Bis zum nächsten Mal!")
    elif data == "BACK_TO_MAIN":
        await show_main_menu(update, context)
    else:
        await query.edit_message_text("Unbekannte Auswahl.")

# --- Top 5 Report ---
async def generate_top5_report(query, context):
    """Generate top 5 coins report using Coingecko data."""
    await query.edit_message_text("📊 Top 5 Investment-Report wird vorbereitet...")
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {"vs_currency": "usd", "order": "market_cap_desc", "per_page": 5, "page": 1}
    try:
        res = requests.get(url, params=params)
        res.raise_for_status()
        data = res.json()
    except Exception as e:
        await query.edit_message_text(f"Fehler beim Abrufen der Daten: {e}")
        return
    report = "**📈 Top 5 Kryptowährungen nach Marktkapitalisierung:**\n\n"
    for coin in data:
        report += (
            f"- {coin['name']} ({coin['symbol'].upper()}): "
            f"Marktkapitalisierung ${coin['market_cap']:,}\n"
        )
    await context.bot.send_message(chat_id=query.from_user.id, text=report, parse_mode="Markdown")

# --- Technical Analysis (RSI) ---
async def calculate_rsi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Calculate RSI for user-provided symbol."""
    symbol = update.message.text.strip().upper()
    await update.message.reply_text(f"🔍 Berechne RSI für {symbol}...")
    coin_id = get_coin_id(symbol)
    if not coin_id:
        await update.message.reply_text("❌ Coin-Symbol nicht gefunden.")
        return
    chart_url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
    params = {"vs_currency": "usd", "days": 30}
    try:
        res = requests.get(chart_url, params=params)
        res.raise_for_status()
        prices = res.json()["prices"]
    except Exception as e:
        await update.message.reply_text(f"Fehler beim Abrufen der Preisdaten: {e}")
        return
    close_prices = [p[1] for p in prices]
    if len(close_prices) < 15:
        await update.message.reply_text("Nicht genügend Daten für RSI.")
        return
    gains = []
    losses = []
    for i in range(1, len(close_prices)):
        change = close_prices[i] - close_prices[i - 1]
        gains.append(max(change, 0))
        losses.append(max(-change, 0))
    avg_gain = sum(gains[-14:]) / 14
    avg_loss = sum(losses[-14:]) / 14
    if avg_loss == 0:
        rsi = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
    await update.message.reply_text(f"📊 Der aktuelle RSI für {symbol} beträgt {rsi:.2f}.")

# --- Social Buzz Analysis ---
async def social_buzz_analysis(query, context):
    """Fetch and present social buzz data (placeholder using global market share)."""
    await query.edit_message_text("📡 Social Buzz Analyse wird erstellt...")
    url = "https://api.coingecko.com/api/v3/global"
    try:
        res = requests.get(url)
        res.raise_for_status()
        data = res.json()["data"]
    except Exception as e:
        await query.edit_message_text(f"Fehler beim Abrufen der Daten: {e}")
        return
    market_share = data.get("market_cap_percentage", {})
    msg = "🔥 **Social Buzz (Marktanteile):**\n"
    for coin, perc in market_share.items():
        msg += f"- {coin.upper()}: {perc:.2f}%\n"
    await context.bot.send_message(chat_id=query.from_user.id, text=msg, parse_mode="Markdown")

# --- GPT/HypeHunter Analysis ---
async def gpt_analysis(query, context):
    """Use HuggingFace API to generate analysis."""
    await query.edit_message_text("🤖 GPT-Auswertung läuft...")
    user_input = "Welche Kryptowährungen sind heute interessant?"
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    payload = {"inputs": user_input}
    try:
        res = requests.post("https://api-inference.huggingface.co/models/gpt2", headers=headers, json=payload)
        res.raise_for_status()
        result = res.json()
        output = result[0].get("generated_text", "Keine Antwort erhalten.")
    except Exception as e:
        output = f"❌ Fehler bei GPT-Auswertung: {e}"
    await context.bot.send_message(chat_id=query.from_user.id, text=output)

# --- Fundamental Data ---
async def fundamental_data(query, context):
    """Show fundamental data using Coingecko global endpoint."""
    await query.edit_message_text("💡 Fundamentaldaten werden gesammelt...")
    url = "https://api.coingecko.com/api/v3/global"
    try:
        res = requests.get(url)
        res.raise_for_status()
        data = res.json()["data"]
    except Exception as e:
        await query.edit_message_text(f"Fehler beim Abrufen der Daten: {e}")
        return
    msg = (
        f"📊 **Gesamtzahl Kryptowährungen:** {data['active_cryptocurrencies']}\n"
        f"💰 **Marktkapitalisierung Gesamt (USD):** ${data['total_market_cap']['usd']:,}\n"
        f"💵 **24h Volumen (USD):** ${data['total_volume']['usd']:,}\n"
        f"🔺 **Bitcoin Dominanz:** {data['market_cap_percentage']['btc']:.2f}%"
    )
    await context.bot.send_message(chat_id=query.from_user.id, text=msg, parse_mode="Markdown")

# --- Portfolio Management ---
async def portfolio_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show portfolio options."""
    user_id = update.effective_user.id
    if user_id not in users_data or not users_data[user_id]["gdpr"]:
        await update.message.reply_text("Bitte starte zuerst mit /start und stimme der DSGVO zu.")
        return
    keyboard = [
        [InlineKeyboardButton("➕ Hinzufügen", callback_data="PORTF_ADD")],
        [InlineKeyboardButton("➖ Entfernen", callback_data="PORTF_REMOVE")],
        [InlineKeyboardButton("📊 Anzeigen", callback_data="PORTF_VIEW")],
        [InlineKeyboardButton("🔙 Zurück", callback_data="BACK_TO_MAIN")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("📁 Portfolio-Verwaltung:", reply_markup=reply_markup)

async def portfolio_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle portfolio inline button callbacks."""
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    if data == "PORTF_ADD":
        context.user_data["portf_action"] = "ADD"
        await query.edit_message_text("🔍 Gib das Symbol und die Menge ein (z.B. BTC 0.5).")
    elif data == "PORTF_REMOVE":
        context.user_data["portf_action"] = "REMOVE"
        await query.edit_message_text("🔍 Gib das Symbol ein, das entfernt werden soll.")
    elif data == "PORTF_VIEW":
        await view_portfolio(query, context)
    elif data == "BACK_TO_MAIN":
        await show_main_menu(update, context)

async def add_to_portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add coin to user's portfolio."""
    parts = update.message.text.strip().split()
    if len(parts) != 2:
        await update.message.reply_text("Falsches Format. Beispiel: BTC 0.5")
        return
    symbol = parts[0].upper()
    try:
        amount = float(parts[1])
    except ValueError:
        await update.message.reply_text("Menge muss eine Zahl sein.")
        return
    user_id = update.effective_user.id
    portfolio = users_data[user_id]["portfolio"]
    portfolio[symbol] = portfolio.get(symbol, 0) + amount
    await update.message.reply_text(f"{amount} {symbol} wurden zum Portfolio hinzugefügt.")

async def remove_from_portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove coin from user's portfolio."""
    symbol = update.message.text.strip().upper()
    user_id = update.effective_user.id
    portfolio = users_data[user_id]["portfolio"]
    if symbol in portfolio:
        del portfolio[symbol]
        await update.message.reply_text(f"{symbol} wurde aus dem Portfolio entfernt.")
    else:
        await update.message.reply_text(f"{symbol} ist nicht in deinem Portfolio.")

async def view_portfolio(query, context):
    """Display user's portfolio with current values."""
    user_id = query.from_user.id
    portfolio = users_data[user_id]["portfolio"]
    if not portfolio:
        await context.bot.send_message(chat_id=user_id, text="Dein Portfolio ist leer.")
        return
    msg = "📑 **Dein Portfolio:**\n"
    total_value = 0
    for sym, amt in portfolio.items():
        coin_id = get_coin_id(sym)
        price = 0
        if coin_id:
            try:
                res = requests.get(
                    "https://api.coingecko.com/api/v3/simple/price",
                    params={"ids": coin_id, "vs_currencies": "usd"},
                )
                price = res.json().get(coin_id, {}).get("usd", 0)
            except:
                price = 0
        val = price * amt
        total_value += val
        msg += f"- {sym}: {amt} Stück, Wert: ${val:,.2f}\n"
    msg += f"\n💰 Gesamtwert: ${total_value:,.2f}"
    await context.bot.send_message(chat_id=user_id, text=msg, parse_mode="Markdown")

# --- Admin Commands ---
@admin_only
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin panel to view statistics."""
    count = len(users_data)
    await update.message.reply_text(f"🚀 Aktive Benutzer: {count}")

@admin_only
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Broadcast message to all users (admin only)."""
    if not context.args:
        await update.message.reply_text("Verwendung: /broadcast <Nachricht>")
        return
    text = " ".join(context.args)
    success = 0
    for uid, info in users_data.items():
        if info.get("gdpr"):
            try:
                await context.bot.send_message(chat_id=uid, text=text)
                success += 1
            except Exception as e:
                logger.error(f"Fehler beim Senden an {uid}: {e}")
    await update.message.reply_text(f"Nachricht an {success} Benutzer gesendet.")

# --- Text Message Handler ---
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("rsi_mode"):
        context.user_data["rsi_mode"] = False
        await calculate_rsi(update, context)
        return
    action = context.user_data.get("portf_action")
    if action == "ADD":
        context.user_data["portf_action"] = None
        await add_to_portfolio(update, context)
        return
    if action == "REMOVE":
        context.user_data["portf_action"] = None
        await remove_from_portfolio(update, context)
        return
    await update.message.reply_text("Unbekannte Eingabe. Bitte nutze das Menü oder /help.")

# --- Scheduled Tasks ---
async def scheduled_top5_report():
    """Scheduled task: send Top5 report to all users."""
    global bot
    if not users_data:
        return
    logger.info("Scheduled: Generating Top5 report for all users.")
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {"vs_currency": "usd", "order": "market_cap_desc", "per_page": 5, "page": 1}
    try:
        res = requests.get(url, params=params)
        res.raise_for_status()
        data = res.json()
    except Exception as e:
        logger.error(f"Scheduled Report - Data fetch failed: {e}")
        return
    report = "**📈 Top 5 Kryptowährungen:**\n\n"
    for coin in data:
        report += f"- {coin['name']} ({coin['symbol'].upper()}): ${coin['current_price']:,}\n"
    for uid, info in users_data.items():
        if info.get("gdpr"):
            try:
                await bot.send_message(chat_id=uid, text=report, parse_mode="Markdown")
            except Exception as e:
                logger.error(f"Fehler beim Senden an {uid}: {e}")

# --- Entry Point ---
    # Scheduler: daily at 9:00 Berlin time
    scheduler = AsyncIOScheduler(timezone=pytz.timezone("Europe/Berlin"))
    scheduler.add_job(scheduled_top5_report, CronTrigger(hour=9, minute=0))
    scheduler.start()

    await app.run_polling()

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()



if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()



if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()


import nest_asyncio
nest_asyncio.apply()


import nest_asyncio
nest_asyncio.apply()


import nest_asyncio
nest_asyncio.apply()

async def main():
    application.add_handler(CommandHandler("start", start))
    scheduler.start()
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    await application.updater.idle()

asyncio.get_event_loop().run_until_complete(main())

import nest_asyncio
nest_asyncio.apply()

async def main():
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("portfolio", zeige_portfolio))
    application.add_handler(CallbackQueryHandler(button_handler))
    scheduler.start()
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    await application.updater.idle()

asyncio.get_event_loop().run_until_complete(main())

import nest_asyncio
nest_asyncio.apply()

async def main():
    application = ApplicationBuilder().token("8020495240:AAG_gCHwdR_hFUaoD57GKSU9dAXVmMlVgVg").build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("portfolio", zeige_portfolio))
    application.add_handler(CallbackQueryHandler(button_handler))
    scheduler.start()
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    await application.updater.idle()

asyncio.get_event_loop().run_until_complete(main())
