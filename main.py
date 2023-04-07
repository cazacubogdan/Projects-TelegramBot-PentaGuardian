import logging
import random
from telegram import Update, ForceReply, ChatPermissions
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from telegram.error import BadRequest
import os
from langdetect import detect_langs

def read_api_key(filename):
    with open(filename, 'r') as f:
        api_key = f.readline().strip()
    return api_key

def load_ids_from_file(filename):
    try:
        with open(filename, 'r') as f:
            ids = set(map(int, f.read().splitlines()))
    except FileNotFoundError:
        ids = set()
    return ids

def save_ids_to_file(filename, ids):
    with open(filename, 'w') as f:
        for id in ids:
            f.write(f'{id}\n')

def generate_challenge():
    a = random.randint(1, 10)
    b = random.randint(1, 10)
    question = f"What is the result of {a} + {b}?"
    answer = a + b
    return question, answer

API_KEY_FILE = '/app/Secrets/api_key_pentabot.txt'
BOT_TOKEN = read_api_key(API_KEY_FILE)

LOG_FILE = '/bot_kicker.log'
logging.basicConfig(
    filename=LOG_FILE,
    filemode='a',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BAN_LIST_FILE = 'ban_list.txt'
EXCEPTIONS_LIST_FILE = 'exceptions_list.txt'
PENDING_USERS_FILE = 'pending_users.txt'
BAN_LIST = load_ids_from_file(BAN_LIST_FILE)
ID_EXCEPTIONS = load_ids_from_file(EXCEPTIONS_LIST_FILE)
PENDING_USERS = load_ids_from_file(PENDING_USERS_FILE)

ALLOWED_LANGUAGES = {'en'}

def start(update: Update, context: CallbackContext):
    update.message.reply_text('Hi! I am PentaGuardian!')

def send_challenge(update: Update, context: CallbackContext, user_id: int):
    challenge, answer = generate_challenge()
    message = context.bot.send_message(chat_id=update.message.chat.id, text=challenge, reply_markup=ForceReply(selective=True))
    context.user_data[user_id] = {'message_id': message.message_id, 'answer': answer}
    return message.message_id

def challenge_response_handler(update: Update, context: CallbackContext):
    user = update.message.from_user
    user_id = user.id

    if user_id not in PENDING_USERS:
        return

    user_data = context.user_data.get(user_id)
    if user_data and user_data['message_id'] == update.message.reply_to_message.message_id:
        handle_challenge_response(update, context, user_id)

def language_checker(update: Update, context: CallbackContext):
    message_text = update.message.text
    detected_languages = detect_langs(message_text)
    for lang in detected_languages:
        if lang.lang in ALLOWED_LANGUAGES:
            return
    update.message.reply_text("Sorry, only English messages are allowed in this chat.")

def new_member_handler(update: Update, context: CallbackContext):
    for user in update.message.new_chat_members:
        user_id = user.id

        # Bot checker
        if user.is_bot:
            context.bot.kick_chat_member(update.message.chat.id, user_id)
            continue

        if user_id in ID_EXCEPTIONS or user_id in BAN_LIST:
            continue

        save_ids_to_file(PENDING_USERS_FILE, PENDING_USERS)

    # Restrict the new user's permissions
    chat_id = update.message.chat.id
    bot = context.bot
    restricted_perms = ChatPermissions(can_send_messages=True)
    bot.restrict_chat_member(chat_id, user_id, restricted_perms)

    # Send the challenge to the new user
    try:
        send_challenge(update, context, user_id)
    except BadRequest as e:
        logger.error(f'Failed to send challenge to user (ID: {user_id}): {e}')

def handle_challenge_response(update: Update, context: CallbackContext, user_id: int):
    response = update.message.text.strip()
    user_data = context.user_data.get(user_id)

    if user_data and response == str(user_data['answer']):
        # Correct answer, remove user from pending users list and lift restrictions
        PENDING_USERS.discard(user_id)
        save_ids_to_file(PENDING_USERS_FILE, PENDING_USERS)

        chat_id = update.message.chat.id
        bot = context.bot
        full_perms = ChatPermissions(
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_polls=False,
            can_send_other_messages=False,
            can_add_web_page_previews=False,
            can_change_info=False,
            can_invite_users=True,
            can_pin_messages=False,
        )
        bot.restrict_chat_member(chat_id, user_id, full_perms)

    else:
        # Incorrect answer or non-human response, ban the user
        chat_id = update.message.chat.id
        bot = context.bot
        try:
            bot.ban_chat_member(chat_id, user_id)
            BAN_LIST.add(user_id)
            save_ids_to_file(BAN_LIST_FILE, BAN_LIST)
            logger.info(f'Banned user (ID: {user_id}) for incorrect challenge response in chat_id {chat_id}')
        except BadRequest as e:
            logger.error(f'Failed to ban user (ID: {user_id}) in chat_id {chat_id}: {e}')

def error(update: Update, context: CallbackContext):
    logger.error(f'Update {update} caused error {context.error}')

def main():
    print("Script is running...")
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(MessageHandler(Filters.status_update.new_chat_members, new_member_handler))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command & Filters.reply, challenge_response_handler))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, language_checker))
    dp.add_error_handler(error)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
