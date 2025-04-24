import os
import json
import discord
from discord.ext import commands
from discord import app_commands
from flask import Flask
from threading import Thread
from colorama import init, Fore

# Colorama init
init(autoreset=True)

# Flask setup
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    thread = Thread(target=run_flask)
    thread.start()

keep_alive()


def save_token(token):
    with open("token.json", "w") as file:
        json.dump({"TOKEN": token}, file)


def display_logo():
    logo = '''
██████╗░██╗██╗░░██╗███████╗██╗░░░░░░█████╗░░██████╗  ░██████╗██████╗░░█████╗░███╗░░░███╗
██╔══██╗██║╚██╗██╔╝██╔════╝██║░░░░░██╔══██╗██╔════╝  ██╔════╝██╔══██╗██╔══██╗████╗░████║
██████╔╝██║░╚███╔╝░█████╗░░██║░░░░░███████║╚█████╗░  ╚█████╗░██████╔╝███████║██╔████╔██║
██╔═══╝░██║░██╔██╗░██╔══╝░░██║░░░░░██╔══██║░╚═══██╗  ░╚═══██╗██╔═══╝░██╔══██║██║╚██╔╝██║
██║░░░░░██║██╔╝╚██╗███████╗███████╗██║░░██║██████╔╝  ██████╔╝██║░░░░░██║░░██║██║░╚═╝░██║
╚═╝░░░░░╚═╝╚═╝░░╚═╝╚══════╝╚══════╝╚═╝░░╚═╝╚═════╝░  ╚═════╝░╚═╝░░░░░╚═╝░░╚═╝╚═╝░░░░░╚═╝
'''
    os.system('cls' if os.name == 'nt' else 'clear')
    print(Fore.RED + logo)


def display_status(connected):
    if connected:
        print(Fore.GREEN + "Status: Connected")
    else:
        print(Fore.RED + "Status: Disconnected")


def load_token():
    try:
        with open("token.json", "r") as file:
            data = json.load(file)
            return data.get("token")
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def token_management():
    os.system('cls' if os.name == 'nt' else 'clear')  # Clears the console
    print(Fore.CYAN + "Automatically loading token...\n")

    token = load_token()
    if token:
        print(Fore.GREEN + f"Token loaded successfully: {token}")
        return token
    else:
        print(Fore.RED + "No token found in token.json.")
        return None


intents = discord.Intents.default()
intents.messages = True  # Enable access to message content
intents.message_content = True  # Enable access to message content specifically
intents.typing = False  # Disable typing intent (optional)
intents.presences = False  # Disable presence updates (optional)

bot = commands.Bot(command_prefix="!", intents=intents)


class SpamButton(discord.ui.View):
    def __init__(self, message):
        super().__init__()
        self.message = message

    @discord.ui.button(label="Spam", style=discord.ButtonStyle.red)
    async def spam_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        for _ in range(5):
            await interaction.followup.send(self.message)


@bot.tree.command(name="spamraid", description="Send a message and generate a button to spam")
@app_commands.describe(message="The message you want to spam")
async def spamraid(interaction: discord.Interaction, message: str):
    view = SpamButton(message)
    await interaction.response.send_message(f"💥 SPAM TEXT 💥 : {message}", view=view, ephemeral=True)


@bot.event
async def on_ready():
    print(Fore.GREEN + f"✅ Bot connected as {bot.user}")
    try:
        await bot.tree.sync()
        print(Fore.GREEN + "✅ Slash commands synced successfully.")
    except Exception as e:
        print(Fore.RED + f"❌ Failed to sync commands: {e}")


if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print(Fore.RED + "❌ DISCORD_TOKEN environment variable is not set.")
