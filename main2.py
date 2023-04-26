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
            context.bot.kick_chat_member(update.effective_chat.id, member.id)
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
            ChatPermissions(can_send_messages=True, can_read_messages=True)
        )

        # Remove the user's answer from user_data
        del context.user_data[user_id]

        # Check if the message is in English
        try:
            language = detect(update.message.text)
            if language != 'en':
                update.message.delete()
        except:
            pass

    else:
        # Ban the user and store their ID in a file
        context.bot.kick_chat_member(update.effective_chat.id, user_id)
        with open("banned_users.txt", "a") as file:
            file.write(f"{user_id}\n")

def main():
    updater = Updater(api_key)

    # Register handlers
    updater.dispatcher.add_handler(MessageHandler(Filters.status_update.new_chat_members, on_new_member))
    updater.dispatcher.add_handler(MessageHandler(Filters.text, on_message))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()