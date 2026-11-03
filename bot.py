import os
import random
import time
from dotenv import load_dotenv
import telebot
from telebot import types

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN is missing from environment variables!")

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# In-memory storage for user data
# Structure: {user_id: {"balance": float, "referrals": int}}
users_db = {}


def get_user_data(user_id: int) -> dict:
    """Retrieve or initialize user data."""
    if user_id not in users_db:
        users_db[user_id] = {"balance": 100.0, "referrals": 0}
    return users_db[user_id]


def build_main_keyboard() -> types.ReplyKeyboardMarkup:
    """Creates the main persistent bottom keyboard."""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("🎰 Casino Games"),
        types.KeyboardButton("💰 Wallet"),
        types.KeyboardButton("🚀 Boost & Referral"),
        types.KeyboardButton("🎁 Daily Bonus")
    )
    return markup


def build_games_inline_keyboard() -> types.InlineKeyboardMarkup:
    """Creates the inline keyboard for choosing casino games."""
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🎲 Dice Roll", callback_data="game_dice"),
        types.InlineKeyboardButton("🎰 Slot Machine", callback_data="game_slots"),
        types.InlineKeyboardButton("🎯 Darts", callback_data="game_darts"),
        types.InlineKeyboardButton("⚽ Penalty Kick", callback_data="game_football"),
        types.InlineKeyboardButton("🏀 Basketball", callback_data="game_basketball"),
        types.InlineKeyboardButton("🪙 Coin Flip (50/50)", callback_data="game_coinflip")
    )
    return markup


# --- COMMAND HANDLERS ---

@bot.message_handler(commands=['start'])
def handle_start(message: types.Message):
    user_id = message.from_user.id
    user_data = get_user_data(user_id)

    # Handle Referral tracking via /start <referrer_id>
    args = message.text.split()
    if len(args) > 1 and args[1].isdigit():
        referrer_id = int(args[1])
        if referrer_id != user_id and referrer_id in users_db:
            # Reward referrer once
            users_db[referrer_id]["balance"] += 50.0
            users_db[referrer_id]["referrals"] += 1
            try:
                bot.send_message(
                    referrer_id, 
                    "🎉 <b>New Referral!</b> You earned <b>+$50</b> for inviting a user!"
                )
            except Exception:
                pass

  welcome_text = (
        f"👋សួស្តី <b>{message.from_user.first_name}</b> មកកាន់ Casino Boost Bot!\n\n"
        f"💳 ប្រាក់សមតុល្យរបស់អ្នក: <b>${user_data['balance']:.2f}</b>\n"
        "លេងហ្គេម បន្ថែមសមតុល្យ និងអញ្ជើញមិត្តភក្តិเพื่อรับរង្វាន់!"
    )
    bot.send_message(user_id, welcome_text, reply_markup=build_main_keyboard())


@bot.message_handler(func=lambda msg: msg.text == "🎰 Casino Games")
def show_casino_menu(message: types.Message):
    bot.send_message(
        message.chat.id, 
        "🎰 <b>Select a Casino Game to Play ($10 per roll/bet):</b>", 
        reply_markup=build_games_inline_keyboard()
    )


@bot.message_handler(func=lambda msg: msg.text == "💰 Wallet")
def show_wallet(message: types.Message):
    user_data = get_user_data(message.from_user.id)
    text = (
        "💼 <b>Your Casino Wallet</b>\n\n"
        f"• Current Balance: <b>${user_data['balance']:.2f}</b>\n"
        f"• Total Referrals: <b>{user_data['referrals']} users</b>"
    )
    bot.send_message(message.chat.id, text)


@bot.message_handler(func=lambda msg: msg.text == "🚀 Boost & Referral")
def show_referral(message: types.Message):
    user_id = message.from_user.id
    bot_info = bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start={user_id}"

    text = (
        "🚀 <b>Boost Your Balance!</b>\n\n"
        "Invite your friends to the bot and get free bonus coins!\n"
        "🎁 <b>Reward:</b> <b>+$50.00</b> for every friend that joins.\n\n"
        f"🔗 <b>Your Invite Link:</b>\n<code>{ref_link}</code>"
    )
    bot.send_message(message.chat.id, text)


@bot.message_handler(func=lambda msg: msg.text == "🎁 Daily Bonus")
def claim_daily_bonus(message: types.Message):
    user_data = get_user_data(message.from_user.id)
    user_data["balance"] += 25.0
    bot.send_message(
        message.chat.id, 
        "🎁 <b>Daily Bonus Claimed!</b>\nAdded <b>+$25.00</b> to your wallet."
    )


# --- GAME LOGIC (INLINE CALLBACK HANDLERS) ---

BET_AMOUNT = 10.0

@bot.callback_query_handler(func=lambda call: call.data.startswith("game_"))
def handle_game_choice(call: types.CallbackQuery):
    user_id = call.from_user.id
    user_data = get_user_data(user_id)

    # Check balance
    if user_data["balance"] < BET_AMOUNT:
        bot.answer_callback_query(
            call.id, 
            text="❌ Insufficient balance! Invite friends to get more funds.", 
            show_alert=True
        )
        return

    game_type = call.data.replace("game_", "")

    # Deduct Bet
    user_data["balance"] -= BET_AMOUNT
    bot.answer_callback_query(call.id, text=f"Bet placed: -${BET_AMOUNT:.2f}")

    if game_type in ["dice", "slots", "darts", "football", "basketball"]:
        # Map game to Telegram Native Interactive Animated Dice
        emoji_map = {
            "dice": "🎲",
            "slots": "🎰",
            "darts": "🎯",
            "football": "⚽",
            "basketball": "🏀"
        }
        emoji = emoji_map[game_type]
        
        # Send animated dice
        msg = bot.send_dice(call.message.chat.id, emoji=emoji)
        score = msg.dice.value
        time.sleep(3)  # Wait for animation to finish

        # Calculate result based on dice score
        if game_type == "slots":
            # 64 = jackpot (777)
            if score == 64:
                payout = 100.0
                result_text = "🎉 <b>JACKPOT! 777!</b> You won <b>+$100.00</b>!"
            elif score in [1, 22, 43]:  # Minor wins
                payout = 25.0
                result_text = "✨ <b>Match!</b> You won <b>+$25.00</b>!"
            else:
                payout = 0.0
                result_text = "❌ No match! Try again."
        
        elif game_type == "dice":
            if score >= 4:
                payout = 20.0
                result_text = f"🎯 Rolled <b>{score}</b>! You won <b>+$20.00</b>!"
            else:
                payout = 0.0
                result_text = f"📉 Rolled <b>{score}</b>. Better luck next time!"

        elif game_type == "darts":
            if score == 6:  # Bullseye
                payout = 30.0
                result_text = "🎯 <b>BULLSEYE!</b> You won <b>+$30.00</b>!"
            elif score >= 3:
                payout = 15.0
                result_text = f"🎯 Hit score <b>{score}</b>! You won <b>+$15.00</b>!"
            else:
                payout = 0.0
                result_text = "❌ Missed the target!"

        elif game_type in ["football", "basketball"]:
            if score >= 4:  # Goal / Swish
                payout = 20.0
                result_text = "⚽/🏀 <b>SCORE!</b> You won <b>+$20.00</b>!"
            else:
                payout = 0.0
                result_text = "❌ Missed!"

        user_data["balance"] += payout
        bot.send_message(
            call.message.chat.id, 
            f"{result_text}\n💰 New Balance: <b>${user_data['balance']:.2f}</b>",
            reply_markup=build_games_inline_keyboard()
        )

    elif game_type == "coinflip":
        outcome = random.choice(["Heads", "Tails"])
        win = random.choice([True, False])

        if win:
            payout = 20.0
            result_text = f"🪙 It landed on <b>{outcome}</b>! You WON <b>+$20.00</b>!"
            user_data["balance"] += payout
        else:
            result_text = f"🪙 It landed on <b>{outcome}</b>. You Lost!"

        bot.send_message(
            call.message.chat.id,
            f"{result_text}\n💰 New Balance: <b>${user_data['balance']:.2f}</b>",
            reply_markup=build_games_inline_keyboard()
        )


if __name__ == "__main__":
    print("Bot is running...")
    bot.infinity_polling(skip_pending=True)
