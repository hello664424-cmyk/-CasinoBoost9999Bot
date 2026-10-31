import os
import logging
from typing import Dict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Simple in-memory user database
# In production, replace this dictionary with PostgreSQL or SQLite
users_db: Dict[int, int] = {}
DEFAULT_BALANCE = 1000

# Game emoji mappings for native Telegram animated dice
GAMES = {
    "slots": {"emoji": "🎰", "name": "Slots", "mult": 3},
    "dice": {"emoji": "🎲", "name": "Dice", "mult": 2},
    "bowling": {"emoji": "🎳", "name": "Bowling", "mult": 2},
    "basketball": {"emoji": "🏀", "name": "Basketball", "mult": 2},
    "darts": {"emoji": "🎯", "name": "Darts", "mult": 2},
    "football": {"emoji": "⚽", "name": "Football", "mult": 2},
}

def get_user_balance(user_id: int) -> int:
    if user_id not in users_db:
        users_db[user_id] = DEFAULT_BALANCE
    return users_db[user_id]

def update_user_balance(user_id: int, amount: int) -> int:
    current = get_user_balance(user_id)
    users_db[user_id] = max(0, current + amount)
    return users_db[user_id]

def build_menu_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("🎰 Slots", callback_data="game_slots"),
            InlineKeyboardButton("🎲 Dice", callback_data="game_dice"),
        ],
        [
            InlineKeyboardButton("🎳 Bowling", callback_data="game_bowling"),
            InlineKeyboardButton("🎯 Darts", callback_data="game_darts"),
        ],
        [
            InlineKeyboardButton("🏀 Basketball", callback_data="game_basketball"),
            InlineKeyboardButton("⚽ Football", callback_data="game_football"),
        ],
        [
            InlineKeyboardButton("💰 Balance", callback_data="action_balance"),
            InlineKeyboardButton("🎁 Daily Bonus (+500)", callback_data="action_bonus"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    balance = get_user_balance(user.id)
    
    welcome_text = (
        f"🎰 *Welcome to the Telegram Casino, {user.first_name}!*\n\n"
        f"💵 *Your Balance:* `{balance}` Coins\n\n"
        "Select a game below to place your bet (Default Bet: 50 Coins):"
    )
    
    await update.message.reply_text(
        text=welcome_text,
        parse_mode="Markdown",
        reply_markup=build_menu_keyboard()
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data

    if data == "action_balance":
        balance = get_user_balance(user_id)
        await query.edit_message_text(
            text=f"💵 *Current Balance:* `{balance}` Coins",
            parse_mode="Markdown",
            reply_markup=build_menu_keyboard()
        )
        return

    if data == "action_bonus":
        new_balance = update_user_balance(user_id, 500)
        await query.edit_message_text(
            text=f"🎁 *Daily Bonus Claimed!* +500 Coins added.\n💵 *New Balance:* `{new_balance}` Coins",
            parse_mode="Markdown",
            reply_markup=build_menu_keyboard()
        )
        return

    if data.startswith("game_"):
        game_key = data.split("_")[1]
        if game_key not in GAMES:
            return

        bet_amount = 50
        current_balance = get_user_balance(user_id)

        if current_balance < bet_amount:
            await query.edit_message_text(
                text=f"❌ *Insufficient Balance!* You need at least {bet_amount} coins to play.\nUse the Daily Bonus button to get free coins.",
                parse_mode="Markdown",
                reply_markup=build_menu_keyboard()
            )
            return

        # Deduct bet upfront
        update_user_balance(user_id, -bet_amount)
        game_info = GAMES[game_key]

        # Send native animated Telegram dice
        msg = await context.bot.send_dice(
            chat_id=query.message.chat_id,
            emoji=game_info["emoji"]
        )

        score = msg.dice.value
        won = False
        payout = 0

        # Win conditions for Telegram animated dice
        if game_key == "slots":
            # Slot value 64 represents jackpot (777)
            if score == 64:
                won = True
                payout = bet_amount * 5
            elif score in [1, 22, 43]:  # Match 3 of identical icons
                won = True
                payout = bet_amount * 3
        else:
            # Dice, Darts, Bowling, Basketball, Football: Win on score >= 4
            if score >= 4:
                won = True
                payout = bet_amount * game_info["mult"]

        if won:
            final_balance = update_user_balance(user_id, payout)
            result_msg = (
                f"🎉 *YOU WON!*\n"
                f"Game: {game_info['name']} {game_info['emoji']}\n"
                f"Score: `{score}`\n"
                f"Prize: `+{payout}` Coins\n"
                f"New Balance: `{final_balance}` Coins"
            )
        else:
            final_balance = get_user_balance(user_id)
            result_msg = (
                f"💥 *YOU LOST!*\n"
                f"Game: {game_info['name']} {game_info['emoji']}\n"
                f"Score: `{score}`\n"
                f"Loss: `-{bet_amount}` Coins\n"
                f"New Balance: `{final_balance}` Coins"
            )

        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=result_msg,
            parse_mode="Markdown",
            reply_markup=build_menu_keyboard()
        )

def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        logger.error("No BOT_TOKEN environment variable found!")
        return

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CallbackQueryHandler(handle_callback))

    logger.info("Bot started successfully...")
    app.run_polling()

if __name__ == "__main__":
    main()
