import logging
import re
import langdetect
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, filters, CallbackContext
from telegram.error import BadRequest

def read_api_key(filename):
    with open(filename, 'r') as f:
        api_key = f.readline().strip()
    return api_key

API_KEY_FILE = '/app/Secrets/api_key_pentabot.txt'
BOT_TOKEN = read_api_key(API_KEY_FILE)

# Set up logging to a specific file
LOG_FILE = 'bot_kicker.log'
logging.basicConfig(
    filename=LOG_FILE,
    filemode='a',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

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

BAN_LIST_FILE = 'ban_list.txt'
EXCEPTIONS_LIST_FILE = 'exceptions_list.txt'
BAN_LIST = load_ids_from_file(BAN_LIST_FILE)
ID_EXCEPTIONS = load_ids_from_file(EXCEPTIONS_LIST_FILE)

def start(bot, update):
    update.message.reply_text('Hi! I am a bot to keep unwanted users and bots out of your channel.')

def bot_pattern(username: str):
    bot_patterns = [
        r'^bot_',
        r'_bot$',
    ]

    for pattern in bot_patterns:
        if re.search(pattern, username, re.IGNORECASE):
            return True
    return False

def bot_checker(bot, update):
    for user in update.message.new_chat_members:
        user_id = user.id

        if user_id in ID_EXCEPTIONS:
            continue

        if user_id in BAN_LIST or user.is_bot or bot_pattern(user.username):
            chat_id = update.message.chat.id
            bot = context.bot
            try:
                bot.kick_chat_member(chat_id, user_id)
                update.message.reply_text(f'Removed user/bot @{user.username} from the channel.')
                logger.info(f'Removed user/bot @{user.username} from chat_id {chat_id}')
                
                BAN_LIST.add(user_id)
                save_ids_to_file(BAN_LIST_FILE, BAN_LIST)
            except BadRequest as e:
                logger.error(f'Failed to remove user/bot @{user.username} from chat_id {chat_id}: {e}')

def check_language(bot, update):
    text = update.message.text
    detected_langs = langdetect.detect_langs(text)
    
    for lang_prob in detected_langs:
        if lang_prob.lang == 'en' and lang_prob.prob > 0.8:
            return

    user = update.message.from_user
    user_id = user.id
    
    if user_id not in ID_EXCEPTIONS:
        chat_id = update.message.chat.id
        bot = context.bot
        try:
            bot.kick_chat_member(chat_id, user_id)
            BAN_LIST.add(user_id)
            save_ids_to_file(BAN_LIST_FILE, BAN_LIST)
            logger.info(f'Banned user @{user.username} (ID: {user_id}) for non-English message in chat_id {chat_id}')
        except BadRequest as e:
            logger.error(f'Failed to ban user @{user.username} (ID: {user_id}) in chat_id {chat_id}: {e}')

def error(bot, update, error):
    logger.error(f'Update {update} caused error {context.error}')

def main():
    updater = Updater(BOT_TOKEN)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(MessageHandler(Filters.status_update.new_chat_members, bot_checker))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, check_language))
    dp.add_error_handler(error)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
