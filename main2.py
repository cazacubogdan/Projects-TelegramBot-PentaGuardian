import os
import logging
import random
from telegram import Update, ChatPermissions
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from langdetect import detect

# What would the code for a python telegram bot with the following requirements, would look like:
# 1. Reads the Telegram bot API key from a file stored in /app/Secrets/api_key_pentabot.txt
# 2. Kicks and bans bots.
# 3. Generates a random math challenge and sends it to new users who join the channel. Restricts new users to prevent them from sending or seeing any group messages before answering the math challenge.
# 4. Checks the language of messages sent in chat after the math challenge is complete, and only allows messages in English.
# 5. Bans users who fail to answer the math challenge correctly, or send non-human responses.
# 6. Stores banned user IDs in a file for persistent storage across bot restarts.
# 7. Sets up logging to a file for debugging purposes and have the posibility to chose various logging levels.
# 8. Send a private message to the user getting banned containing the reason of the ban and at the same time to post a message on the group saying what user has been banned and why

# Read API key from file
with open("/app/Secrets/api_key_pentabot.txt", "r") as file:
    api_key = file.read().strip()

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

        # # Check if the message is in English
        # try:
        #     language = detect(update.message.text)
        #     if language != 'en':
        #         update.message.delete()
        # except:
        #     pass

    else:
        # 
        ban_reason = "Failed to answer the math challenge correctly or non-human response"
        ban_user(user_id, update.effective_chat.id, ban_reason, context)
        with open("banned_users.txt", "a") as file:
            file.write(f"{user_id}\n")


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
        text=f"User with ID {user_id} has been banned due to: {ban_reason}"
    )

def main():
    updater = Updater(api_key)

    # Register handlers
    updater.dispatcher.add_handler(MessageHandler(Filters.status_update.new_chat_members, on_new_member))
    updater.dispatcher.add_handler(MessageHandler(Filters.text, on_message))
    updater.dispatcher.add_handler(MessageHandler(Filters.text, check_english))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()