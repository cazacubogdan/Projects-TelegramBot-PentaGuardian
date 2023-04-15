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
#logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

#=========================================================
#debug
#=========================================================

# Create a logger object
logger = logging.getLogger(__name__)

# Set the logging level to DEBUG
logger.setLevel(logging.DEBUG)

# Create a file handler to save the logs to a file
file_handler = logging.FileHandler('bot.log')
file_handler.setLevel(logging.DEBUG)

# Create a stream handler to output the logs to the console
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)

# Define the log message format
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)

# Add the handlers to the logger
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

#=========================================================

# Initialize the updater and dispatcher
updater = Updater(api_key, use_context=True)
dispatcher = updater.dispatcher

# Define the global variables and constants
USER_DATA_FILE = "user_data.json"
EXCEPTIONS_FILE = "exceptions.json"
LAST_MESSAGES_FILE = "last_messages.json"
#last_messages_file = {}
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


#===#debug
# Define the check_new_members handler with logging statements
def check_new_members(update, context):
    logger.info("New member joined the group")

    for member in update.message.new_chat_members:
        challenge_message = "Welcome, please solve this math operation: {} + {}".format(random.randint(0, 10), random.randint(0, 10))
        context.bot.send_message(chat_id=update.message.chat_id, text=challenge_message, reply_to_message_id=update.message.message_id)
        logger.info("Challenge message sent to new member: %s", challenge_message)

        user_data[member.id] = {"last_challenge_timestamp": int(time.time()), "is_bot": member.is_bot}
        logger.debug("User data saved for member %d: %s", member.id, user_data[member.id])

    save_user_data()
    logger.debug("User data saved to file")
#===
# def check_new_members(update, context):
#     # Log a message to confirm that the handler is being triggered
#     logger.info("New member joined the group")

#     for member in update.message.new_chat_members:
#         if member.is_bot:
#             update.message.reply_text("01010011 01101111 01110010 01110010 01111001 00101100 00100000 01100010 01101111 01110100 01110011 00100000 01100001 01110010 01100101 00100000 01101110 01101111 01110100 00100000 01100001 01101100 01101100 01101111 01110111 01100101 01100100 00100000 01101001 01101110 00100000 01110100 01101000 01101001 01110011 00100000 01100111 01110010 01101111 01110101 01110000 00101110")
#             context.bot.kick_chat_member(update.message.chat_id, member.id)
#         else:
#         # Send the challenge message to the new member and log a message to confirm
#         challenge_message = "Welcome, please solve this math operation: {} + {}".format(random.randint(0, 10), random.randint(0, 10))
#         context.bot.send_message(chat_id=update.message.chat_id, text=challenge_message, reply_to_message_id=update.message.message_id)
#         logger.info("Challenge message sent to new member: %s", challenge_message)

#         # Save the user data for the new member
#         user_data[member.id] = {"last_challenge_timestamp": int(time.time()), "is_bot": member.is_bot}

#     # Save the user data to file
#     save_user_data()
#===

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
#===#debug
# Define the check_no_spam handler with logging statements
def check_no_spam(update, context):
    logger.info("Message received: %s", update.message.text)

    try:
        user_id = update.message.from_user.id
        timestamp = int(time.time())

        # Check if the user is exempt from spam checking
        if user_id in exceptions:
            return

        # Check if the user has sent too many messages in the last 10 seconds
        last_messages = LAST_MESSAGES_FILE.get(user_id, [])
        last_messages.append(timestamp)
        last_messages = [t for t in last_messages if timestamp - t < 10]
        LAST_MESSAGES_FILE[user_id] = last_messages

        if len(last_messages) > MAX_MESSAGES_PER_10_SECONDS:
            context.bot.delete_message(chat_id=update.message.chat_id, message_id=update.message.message_id)
            logger.info("Message deleted due to spam: %s", update.message.text)
        else:
            logger.debug("Message allowed: %s", update.message.text)

        save_last_messages()
        logger.debug("Last messages data saved to file")
    except Exception as e:
        logger.error("Error in check_no_spam handler: %s", e)
# ===
# def check_no_spam(update, context):
#     user_id = update.effective_user.id
#     if user_id in exceptions:
#         return
#     if user_id not in last_messages:
#         last_messages[user_id] = {"times": [int(time.time())]}
#     else:
#         times = last_messages[user_id]["times"]
#         times.append(int(time.time()))
#         while len(times) > SPAM_LIMIT:
#             times.pop(0)
#         last_messages[user_id]["times"] = times
#         if times[-1] - times[0] < TIMEFRAME:
#             update.message.reply_text(NO_SPAM_MESSAGE)
#             if user_id not in user_data:
#                 user_data[user_id] = {"warnings": 1, "banned": False, "last_warning_timestamp": int(time.time())}
#             else:
#                 user_data[user_id]["warnings"] += 1
#                 if user_data[user_id]["warnings"] > WARNINGS_BEFORE_BAN:
#                     if not user_data[user_id]["banned"]:
#                         context.bot.kick_chat_member(update.message.chat_id, user_id)
#                         user_data[user_id]["banned"] = True
#                         update.message.reply_text(BAN_MESSAGE)
#                 else:
#                     update.message.reply_text(WARNING_MESSAGE)
#             save_user_data()
#     save_last_messages()
#===
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

#===
#debug
#===
# Create a handler to handle errors
def error_handler(update, context):
    logger.error("An error occurred: %s", context.error)
#===

# Define the handlers and add them to the dispatcher
dispatcher.add_handler(MessageHandler(Filters.status_update.new_chat_members, check_new_members))

# Comment out the check_english_only handler
# dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command & Filters.chat_type.groups, check_english_only))

# Comment out the check_no_links handler
# dispatcher.add_handler(MessageHandler(Filters.text & Filters.entity('url') & Filters.chat_type.groups, check_no_links))

# Comment out the check_no_spam handler
dispatcher.add_handler(MessageHandler(Filters.text & Filters.chat_type.groups, check_no_spam))

dispatcher.add_handler(CommandHandler('unban', unban_user))

dispatcher.add_error_handler(error_handler)

# Start the bot
updater.start_polling()
updater.idle()

# Save the data to files on exit
save_user_data()
save_exceptions()
save_last_messages()
