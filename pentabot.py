import os
import logging
import random
import re
import time
from telegram import Update, ChatPermissions
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from langdetect import detect

# Read API key from file
with open("/app/Secrets/api_key_pentabot.txt", "r") as file:
    api_key = file.read().strip()

with open("spam_exceptions.txt", "r") as file:
    spam_exceptions = [line.strip() for line in file.readlines()]

with open("links_exceptions.txt", "r") as file:
    links_exceptions = [line.strip() for line in file.readlines()]


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("pentabot.log"), logging.StreamHandler()]
)

logger = logging.getLogger()

def generate_math_challenge():
    a = random.randint(1, 100)
    b = random.randint(1, 100)
    question = f"{a} + {b}"
    answer = a + b
    return question, answer

def on_new_member(update: Update, context: CallbackContext):
    new_members = update.message.new_chat_members
    for member in new_members:
        if member.is_bot:
            ban_user(member.id, update.effective_chat.id, "Bot detected", context)
            continue
        
        # Generate a math challenge
        question, answer = generate_math_challenge()

        # Store the correct answer in user_data
        context.user_data[member.id] = {"answer": answer}

        # Send the math challenge to the group chat
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Welcome, {member.first_name}! Please answer the following math question to join the group: {question}"
        )

        # Restrict the new user but allow them to send messages
        context.bot.restrict_chat_member(
            update.effective_chat.id,
            member.id,
            ChatPermissions(can_send_messages=True)
        )

def on_message(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id

    # If the user is not in user_data, they have not been challenged yet
    if user_id not in context.user_data:
        # check_english(update, context)  # Uncomment this line
        return

    # Check if the answer is correct
    try:
        answer = int(update.message.text.strip())
    except ValueError:
        answer = None

    if answer == context.user_data[user_id]["answer"]:
        # Unrestrict the user if they answered correctly
        context.bot.restrict_chat_member(
            update.effective_chat.id,
            user_id,
            ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_polls=False,
                can_send_other_messages=False,
                can_add_web_page_previews=False,
                can_change_info=False,
                can_invite_users=True,
                can_pin_messages=False,
                can_read_messages=True
            )
        )

        # Remove the user's answer from user_data
        del context.user_data[user_id]

        # check_english(update, context)  # Uncomment this line

    else:
        ban_reason = "Failed to answer the math challenge correctly or non-human response"
        ban_user(user_id, update.effective_chat.id, ban_reason, context)
        with open("banned_users.txt", "a") as file:
            file.write(f"{user_id}\n")

    check_spam(update, context)  # Uncomment this line
    check_links(update, context)  # Uncomment this line

def check_english(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id

    # If the user is in user_data, they have not completed the challenge yet
    if user_id in context.user_data:
        return

    try:
        language = detect(update.message.text)
        if language != 'en':
            # 
            ban_reason = "Non-English message"
            ban_user(user_id, update.effective_chat.id, ban_reason, context)
            with open("banned_users.txt", "a") as file:
                file.write(f"{user_id}\n")
            update.message.delete()
    except:
        pass

def ban_user(user_id, chat_id, ban_reason, context: CallbackContext):
    # Ban the user
    context.bot.ban_chat_member(chat_id, user_id)

    # Get user info for the banned user
    user_info = context.bot.get_chat_member(chat_id, user_id).user

    # Send a private message to the user
    try:
        context.bot.send_message(
            chat_id=user_id,
            text=f"You have been banned from the group due to: {ban_reason}"
        )
    except Exception as e:
        logger.error(f"Failed to send private message to banned user: {e}")

    # Post a message in the group
    context.bot.send_message(
        chat_id=chat_id,
        text=f"User {user_info.first_name} has been banned due to: {ban_reason}"
    )

def check_spam(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id

    if str(user_id) in spam_exceptions:
        return

    if 'last_message_time' not in context.user_data:
        context.user_data['last_message_time'] = {}

    if user_id not in context.user_data['last_message_time']:
        context.user_data['last_message_time'][user_id] = time.time()
        return

    current_time = time.time()
    time_difference = current_time - context.user_data['last_message_time'][user_id]

    if time_difference < 5:  # Adjust the time threshold for spamming as needed
        ban_reason = "Spamming"
        ban_user(user_id, update.effective_chat.id, ban_reason, context)

    context.user_data['last_message_time'][user_id] = current_time

def check_links(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id

    if str(user_id) in links_exceptions:
        return

    message_text = update.message.text
    link_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
    links = re.findall(link_pattern, message_text)

    if len(links) > 0:
        update.message.delete()  # Delete the message containing the link(s)
        ban_reason = "Sending links"
        ban_user(user_id, update.effective_chat.id, ban_reason, context)

def main():
    updater = Updater(api_key)

    # Register handlers
    updater.dispatcher.add_handler(MessageHandler(Filters.status_update.new_chat_members, on_new_member))
    updater.dispatcher.add_handler(MessageHandler(Filters.text, on_message))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()