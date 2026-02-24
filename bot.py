import logging
import threading
import time
from challenge_api import fetch_challenge_image
from evaluation_api import evaluate_prompt
import bot_secrets
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# =============================
# CONFIG
# =============================

GROUP_LINK = bot_secrets.TG_GROUP_LINK

logging.basicConfig(
    format="[%(levelname)s %(asctime)s %(module)s:%(lineno)d] %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)
bot = telebot.TeleBot(bot_secrets.TOKEN)

# =============================
# GAME STATE
# =============================

game_lock = threading.Lock()

game_state = {
    "status": "IDLE",  # IDLE | LOBBY | GUESSING
    "group_id": None,
    "players": set(),
    "guesses": {},
    "waiting_for_guess": set(),
    "lobby_message_id": None,
    "guess_message_id": None,
    "guess_end_time": None,
    "challenge_image_id": None,
}

# =============================
# /start
# =============================

@bot.message_handler(commands=["start"])
def handle_start(message):
    logger.info(f"+ Start chat #{message.chat.id} from {message.chat.username}")

    if message.chat.type != "private":
        bot.reply_to(message, "Please DM me to interact with the bot.")
        return

    parts = message.text.split()

    if len(parts) > 1 and parts[1] == "guess":
        handle_guess_command(message)
        return

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🚀 Join Official Group", url=GROUP_LINK))

    bot.send_message(
        message.chat.id,
        "🎮 *Welcome to the Image Guessing Game!*\n\n"
        "Click below to join the official group.",
        reply_markup=markup,
        parse_mode="Markdown"
    )

# =============================
# /guess
# =============================

@bot.message_handler(commands=["guess"])
def handle_guess_command(message):

    if message.chat.type != "private":
        bot.reply_to(message, "Please DM me to submit your guess.")
        return

    with game_lock:
        if game_state["status"] != "GUESSING":
            bot.reply_to(message, "There is no active guessing phase.")
            return

        user_id = message.from_user.id

        if user_id not in game_state["players"]:
            bot.reply_to(message, "You are not part of this game.")
            return

        if user_id in game_state["guesses"]:
            bot.reply_to(message, "You already submitted your guess.")
            return

        game_state["waiting_for_guess"].add(user_id)

    bot.reply_to(message, "✍️ Please send me your image prompt now.")

# =============================
# /start_game
# =============================

@bot.message_handler(commands=["start_game"])
def start_game(message):

    if message.chat.type not in ["group", "supergroup"]:
        bot.reply_to(message, "This command can only be used in a group.")
        return

    with game_lock:
        if game_state["status"] != "IDLE":
            bot.reply_to(message, "⚠️ A game is already running.")
            return

        game_state["status"] = "LOBBY"
        game_state["group_id"] = message.chat.id
        game_state["players"] = set()

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🎮 Join Game", callback_data="join_game"))

    sent = bot.send_message(
        message.chat.id,
        "🎮 *New Game Starting!*\n\n"
        "Time to join: 30s\n"
        "Players joined: 0",
        reply_markup=markup,
        parse_mode="Markdown",
    )

    with game_lock:
        game_state["lobby_message_id"] = sent.message_id

    threading.Thread(target=lobby_countdown).start()

# =============================
# JOIN BUTTON
# =============================

@bot.callback_query_handler(func=lambda call: call.data == "join_game")
def handle_join(call):

    with game_lock:
        if game_state["status"] != "LOBBY":
            bot.answer_callback_query(call.id, "Lobby closed.")
            return

        user_id = call.from_user.id

        if user_id in game_state["players"]:
            bot.answer_callback_query(call.id, "Already joined.")
            return

        game_state["players"].add(user_id)

    bot.answer_callback_query(call.id, "You joined!")

# =============================
# LOBBY COUNTDOWN (CLEAN)
# =============================

def lobby_countdown():

    remaining = 30

    while remaining > 0:

        with game_lock:
            if game_state["status"] != "LOBBY":
                return
            group_id = game_state["group_id"]
            message_id = game_state["lobby_message_id"]
            player_count = len(game_state["players"])

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🎮 Join Game", callback_data="join_game"))

        try:
            bot.edit_message_text(
                "🎮 *New Game Starting!*\n\n"
                f"Time to join: {remaining}s\n"
                f"Players joined: {player_count}",
                chat_id=group_id,
                message_id=message_id,
                parse_mode="Markdown",
                reply_markup=markup,
            )
        except Exception as e:
            if "message is not modified" not in str(e):
                logger.warning(f"Lobby edit error: {e}")

        if remaining > 10:
            sleep_time = 5
            remaining -= 5
        else:
            sleep_time = 1
            remaining -= 1

        time.sleep(sleep_time)

    end_lobby()

# =============================
# END LOBBY → GUESSING
# =============================

def end_lobby():

    # First validate lobby state safely
    with game_lock:
        group_id = game_state["group_id"]

        if len(game_state["players"]) < 1:
            bot.send_message(group_id, "❌ No players joined.")
            reset_game()
            return

        # Move to guessing state
        game_state["status"] = "GUESSING"
        game_state["guesses"] = {}
        game_state["waiting_for_guess"] = set()
        game_state["guess_end_time"] = time.time() + 30

    # Prepare deep link
    bot_username = bot.get_me().username
    deep_link = f"https://t.me/{bot_username}?start=guess"

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✍️ Submit Guess Privately", url=deep_link)
    )

    # 🔥 Fetch image from API (outside lock)
    try:
        image_bytes, image_id = fetch_challenge_image(bot_secrets.API1_URL)
    except Exception as e:
        bot.send_message(group_id, f"⚠️ Failed to fetch challenge image: {e}")
        reset_game()
        return

    # Store image_id safely
    with game_lock:
        game_state["challenge_image_id"] = image_id

    # Send image from memory (no temp file)
    try:
        sent = bot.send_photo(
            group_id,
            photo=image_bytes,
            caption="🖼 *Describe this image!*\n\n"
                    "You have 30 seconds.",
            parse_mode="Markdown",
            reply_markup=markup,
        )
    except Exception as e:
        bot.send_message(group_id, f"⚠️ Failed to send image: {e}")
        reset_game()
        return

    # Store message id for countdown editing
    with game_lock:
        game_state["guess_message_id"] = sent.message_id

    # Start guess countdown thread
    threading.Thread(target=guess_countdown).start()
# =============================
# GUESS COUNTDOWN (CLEAN)
# =============================

def guess_countdown():

    remaining = 30
    bot_username = bot.get_me().username
    deep_link = f"https://t.me/{bot_username}?start=guess"

    while remaining > 0:

        with game_lock:
            if game_state["status"] != "GUESSING":
                return

            group_id = game_state["group_id"]
            message_id = game_state["guess_message_id"]
            guess_count = len(game_state["guesses"])

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("✍️ Submit Guess Privately", url=deep_link))

        try:
            bot.edit_message_caption(
                caption="🖼 *Describe this image!*\n\n"
                        f"Time remaining: {remaining}s\n"
                        f"Guesses: {guess_count}",
                chat_id=group_id,
                message_id=message_id,
                parse_mode="Markdown",
                reply_markup=markup,
            )
        except Exception as e:
            if "message is not modified" not in str(e):
                logger.warning(f"Guess edit error: {e}")

        if remaining > 10:
            sleep_time = 5
            remaining -= 5
        else:
            sleep_time = 1
            remaining -= 1

        time.sleep(sleep_time)

    end_guess_phase()

def end_guess_phase():

    with game_lock:
        group_id = game_state["group_id"]
        image_id = game_state.get("challenge_image_id")
        guesses_copy = dict(game_state["guesses"])

    if not guesses_copy:
        bot.send_message(group_id, "⏰ Guess phase ended!\nNo guesses submitted.")
        reset_game()
        return

    bot.send_message(group_id, "🧠 Evaluating guesses... Please wait.")

    results = []

    # Evaluate each player
    for user_id, prompt in guesses_copy.items():
        try:
            score, image_bytes = evaluate_prompt(
                bot_secrets.API2_URL,
                image_id,
                prompt
            )
        except Exception as e:
            logger.warning(f"Evaluation failed for {user_id}: {e}")
            continue

        # Fetch username safely (outside lock)
        try:
            user = bot.get_chat(user_id)
            username = user.username or user.first_name or str(user_id)
        except Exception:
            username = str(user_id)

        results.append({
            "user_id": user_id,
            "username": username,
            "prompt": prompt,
            "score": score,
            "image_bytes": image_bytes,
        })

    if not results:
        bot.send_message(group_id, "⚠️ Evaluation failed for all players.")
        reset_game()
        return

    # Sort by score descending
    results.sort(key=lambda x: x["score"], reverse=True)

    # Build result summary
    result_text = "🏆 *Game Results*\n\n"

    for i, r in enumerate(results):
        rank_emoji = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else "🔹"
        result_text += (
            f"{rank_emoji} *{r['username']}* — "
            f"*{round(r['score'], 2)}*\n"
        )

    bot.send_message(group_id, result_text, parse_mode="Markdown")

    # Send generated images
    for r in results:
        caption = (
            f"👤 *{r['username']}*\n"
            f"Score: *{round(r['score'], 2)}*\n\n"
            f"Prompt:\n{r['prompt']}"
        )

        try:
            bot.send_photo(
                group_id,
                photo=r["image_bytes"],
                caption=caption,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.warning(f"Failed to send generated image: {e}")

    reset_game()
# =============================
# DM MESSAGE HANDLER
# =============================

@bot.message_handler(func=lambda m: True)
def handle_messages(message):

    if message.chat.type != "private":
        return

    with game_lock:
        if game_state["status"] != "GUESSING":
            bot.reply_to(message, "There is no active guessing phase.")
            return

        if time.time() > game_state["guess_end_time"]:
            bot.reply_to(message, "⏰ Time is up! You can no longer submit a guess.")
            return

        user_id = message.from_user.id

        if user_id not in game_state["waiting_for_guess"]:
            return

        if user_id in game_state["guesses"]:
            bot.reply_to(message, "You already submitted your guess.")
            return

        game_state["guesses"][user_id] = message.text
        game_state["waiting_for_guess"].remove(user_id)

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔙 Return to Group", url=GROUP_LINK))

    bot.reply_to(message, "✅ Guess received!", reply_markup=markup)

# =============================
# RESET
# =============================

def reset_game():
    with game_lock:
        game_state.update({
            "status": "IDLE",
            "group_id": None,
            "players": set(),
            "guesses": {},
            "waiting_for_guess": set(),
            "lobby_message_id": None,
            "guess_message_id": None,
            "guess_end_time": None,
        })

# =============================
# START BOT
# =============================

logger.info("> Starting bot")
bot.infinity_polling()
logger.info("< Goodbye!")