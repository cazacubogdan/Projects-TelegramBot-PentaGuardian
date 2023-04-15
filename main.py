import logging
import random
import json
import time
from telegram import ParseMode, ChatPermissions
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

# Load API key from file
with open('/app/Secrets/api_key_pentabot.txt') as f:
    api_key = f.read().strip()

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Initialize the updater and dispatcher
updater = Updater(api_key, use_context=True)
dispatcher = updater.dispatcher

# Define the global variables and constants
USER_DATA_FILE = "user_data.json"
EXCEPTIONS_FILE = "exceptions.json"
LAST_MESSAGES_FILE = "last_messages.json"
NO_LINKS_MESSAGE = "Posting links is not allowed in this group."
NO_SPAM_MESSAGE = "Sending too many messages too quickly is not allowed in this group."
ENGLISH_ONLY_MESSAGE = "Please speak English in this group as it is the only language accepted."
BAN_MESSAGE = "You have been banned from this group for breaking the rules."
WARNING_MESSAGE = "Please follow the rules. This is your only warning. Further violations will result in banning."
UNBAN_MESSAGE = "User has been unbanned."
TIMEFRAME = 10  # seconds
WARN_TIMEFRAME = 86400  # seconds
WARNINGS_BEFORE_BAN = 1
SPAM_LIMIT = 3

# Load the user data from file, if available
try:
    with open(USER_DATA_FILE, "r") as f:
        user_data = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    user_data = {}

# Load the exceptions list from file, if available
try:
    with open(EXCEPTIONS_FILE, "r") as f:
        exceptions = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    exceptions = []

# Load the last messages data from file, if available
try:
    with open(LAST_MESSAGES_FILE, "r") as f:
        last_messages = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    last_messages = {}

# Define the helper functions
def save_user_data():
    with open(USER_DATA_FILE, "w") as f:
        json.dump(user_data, f)

def save_exceptions():
    with open(EXCEPTIONS_FILE, "w") as f:
        json.dump(exceptions, f)

def save_last_messages():
    with open(LAST_MESSAGES_FILE, "w") as f:
        json.dump(last_messages, f)

def check_new_members(update, context):
    for member in update.message.new_chat_members:
        if member.is_bot:
            update.message.reply_text("01010011 01101111 01110010 01110010 01111001 00101100 00100000 01100010 01101111 01110100 01110011 00100000 01100001 01110010 01100101 00100000 01101110 01101111 01110100 00100000 01100001 01101100 01101100 01101111 01110111 01100101 01100100 00100000 01101001 01101110 00100000 01110100 01101000 01101001 01110011 00100000 01100111 01110010 01101111 01110101 01110000 00101110")
            context.bot.kick_chat_member(update.message.chat_id, member.id)
        else:
            context.user_data[member.id] = {'last_message_timestamp': 0}
            challenge_message = f"Welcome, {member.first_name}! Please solve this math operation: {random.randint(0, 10)} + {random.randint(0, 10)}"
            update.message.reply_text(challenge_message)

def check_no_links(update, context):
    user_id = update.effective_user.id
    if user_id in exceptions:
        return
    if update.message.entities and any(entity.type == 'url' for entity in update.message.entities):
        update.message.reply_text(NO_LINKS_MESSAGE)
        if user_id not in user_data:
            user_data[user_id] = {"warnings": 1, "banned": False, "last_warning_timestamp": int(time.time())}
        else:
            user_data[user_id]["warnings"] += 1
            if user_data[user_id]["warnings"] > WARNINGS_BEFORE_BAN:
                if not user_data[user_id]["banned"]:
                    context.bot.kick_chat_member(update.message.chat_id, user_id)
                    user_data[user_id]["banned"] = True
                    update.message.reply_text(BAN_MESSAGE)
            else:
                update.message.reply_text(WARNING_MESSAGE)
            save_user_data()

def check_no_spam(update, context):
    user_id = update.effective_user.id
    if user_id in exceptions:
        return
    if user_id not in last_messages:
        last_messages[user_id] = {"times": [int(time.time())]}
    else:
        times = last_messages[user_id]["times"]
        times.append(int(time.time()))
        while len(times) > SPAM_LIMIT:
            times.pop(0)
        last_messages[user_id]["times"] = times
        if times[-1] - times[0] < TIMEFRAME:
            update.message.reply_text(NO_SPAM_MESSAGE)
            if user_id not in user_data:
                user_data[user_id] = {"warnings": 1, "banned": False, "last_warning_timestamp": int(time.time())}
            else:
                user_data[user_id]["warnings"] += 1
                if user_data[user_id]["warnings"] > WARNINGS_BEFORE_BAN:
                    if not user_data[user_id]["banned"]:
                        context.bot.kick_chat_member(update.message.chat_id, user_id)
                        user_data[user_id]["banned"] = True
                        update.message.reply_text(BAN_MESSAGE)
                else:
                    update.message.reply_text(WARNING_MESSAGE)
            save_user_data()
    save_last_messages()

def check_english_only(update, context):
    user_id = update.effective_user.id
    if user_id in exceptions:
        return
    if update.message.from_user.language_code.lower() != 'en':
        update.message.reply_text(ENGLISH_ONLY_MESSAGE)
        if user_id not in user_data:
            user_data[user_id] = {"warnings": 1, "banned": False, "last_warning_timestamp": int(time.time())}
        else:
            user_data[user_id]["warnings"] += 1
            if user_data[user_id]["warnings"] > WARNINGS_BEFORE_BAN:
                if not user_data[user_id]["banned"]:
                    context.bot.kick_chat_member(update.message.chat_id, user_id)
                    user_data[user_id]["banned"] = True
                    update.message.reply_text(BAN_MESSAGE)
            else:
                update.message.reply_text(WARNING_MESSAGE)
        save_user_data()

def unban_user(update, context):
    if update.message.chat.type != 'supergroup':
        update.message.reply_text("This command can only be used in a supergroup.")
        return
    if not update.message.reply_to_message:
        update.message.reply_text("Please reply to the message of the user you want to unban.")
        return
    user_id = update.message.reply_to_message.from_user.id
    context.bot.unban_chat_member(update.message.chat_id, user_id)
    update.message.reply_text(UNBAN_MESSAGE)
    if user_id in user_data:
        user_data[user_id]["banned"] = False
        user_data[user_id]["warnings"] = 0
        save_user_data()

# Define the handlers and add them to the dispatcher
dispatcher.add_handler(MessageHandler(Filters.status_update.new_chat_members, check_new_members))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command & Filters.chat_type.groups, check_english_only))
dispatcher.add_handler(MessageHandler(Filters.text & Filters.entity('url') & Filters.chat_type.groups, check_no_links))
dispatcher.add_handler(MessageHandler(Filters.text & Filters.chat_type.groups, check_no_spam))
dispatcher.add_handler(CommandHandler('unban', unban_user))

# Start the bot
updater.start_polling()
updater.idle()

# Save the data to files on exit
save_user_data()
save_exceptions()
save_last_messages()
