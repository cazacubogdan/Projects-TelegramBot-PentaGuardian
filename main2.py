# import necessary libraries and modules
import logging
import random
import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

# read the Telegram bot API key from api_key_pentabot.txt
with open('/app/Secrets/api_key_pentabot.txt', 'r') as f:
    TOKEN = f.read().strip()

# create a Telegram bot object
bot = telegram.Bot(token=TOKEN)

# create a function to generate a random math challenge
def generate_challenge():
    num1 = random.randint(1, 100)
    num2 = random.randint(1, 100)
    operator = random.choice(['+', '-', '*', '/'])
    if operator == '+':
        answer = num1 + num2
    elif operator == '-':
        answer = num1 - num2
    elif operator == '*':
        answer = num1 * num2
    else:
        answer = num1 / num2
    challenge = f"What is {num1} {operator} {num2}?"
    return challenge, answer

# create a function to check if a message is in English or not
def is_english(message):
    try:
        message.encode(encoding='utf-8').decode('ascii')
    except UnicodeDecodeError:
        return False
    else:
        return True

# create a function to ban users who fail to answer the math challenge correctly or send non-human responses
def ban_user(bot, chat_id, user_id):
    bot.kick_chat_member(chat_id, user_id)
    with open('banned_users_list.txt', 'a') as f:
        f.write(str(user_id) + '\n')

# create a function to kick bots and restrict new users until they answer the math challenge
def kick_or_restrict(bot, update):
    user = update.message.new_chat_members[0]
    chat_id = update.message.chat_id
    user_id = user.id
    # kick bots
    if user.is_bot:
        bot.kick_chat_member(chat_id, user_id)
    # restrict new users until they answer the math challenge
    else:
        challenge, answer = generate_challenge()
        bot.restrict_chat_member(chat_id, user_id, until_date=time.time()+300, can_send_messages=False)
        bot.send_message(chat_id, f"Welcome {user.username}! Please solve this math challenge within 5 minutes to join the chat: {challenge}")
        with open('pending_users.txt', 'a') as f:
            f.write(str(user_id) + ',' + str(answer) + '\n')

# create a function to store banned user IDs in a file for persistent storage across bot restarts
def load_banned_users():
    try:
        with open('banned_users_list.txt', 'r') as f:
            banned_users = [int(line.strip()) for line in f.readlines()]
    except FileNotFoundError:
        banned_users = []
    return banned_users

def main():
    # set up logging
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    logger = logging.getLogger(__name__)

    # create an updater object and dispatcher object
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # load banned users
    banned_users = load_banned_users()

    # handle new users joining the group chat
    dp.add_handler(MessageHandler(Filters.status_update.new_chat_members, kick_or_restrict))

    # handle messages sent in the group chat
    def message_handler(bot, update):
        message = update.message
        chat_id = message.chat_id
        user_id = message.from_user.id
        username = message.from_user.username
        # check if message is in English
        if not is_english(message.text):
            bot.delete_message(chat_id, message.message_id)
            ban_user(bot, chat_id, user_id)
            logger.warning(f"Banned user {username} ({user_id}) for sending non-English message")
        # check if user is pending (i.e., hasn't answered the math challenge yet)
        elif str(user_id) in open('pending_users.txt').read():
            with open('pending_users.txt', 'r+') as f:
                lines = f.readlines()
                f.seek(0)
                for line in lines:
                    if str(user_id) not in line:
                        f.write(line)
                f.truncate()
            answer = int(message.text)
            with open('pending_users.txt', 'r') as f:
                lines = f.readlines()
            for line in lines:
                if str(user_id) in line:
                    _, correct_answer = line.strip().split(',')
                    break
            if answer == int(correct_answer):
                bot.restrict_chat_member(chat_id, user_id, can_send_messages=True)
                bot.send_message(chat_id, f"Congratulations {username}! You have solved the math challenge and can now chat with us.")
            else:
                bot.kick_chat_member(chat_id, user_id)
                with open('banned_users_list.txt', 'a') as f:
                    f.write(str(user_id) + '\n')
                logger.warning(f"Banned user {username} ({user_id}) for failing the math challenge")
        # handle messages from non-pending users
        else:
            pass

    dp.add_handler(MessageHandler(Filters.text, message_handler))

    # start the bot
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
