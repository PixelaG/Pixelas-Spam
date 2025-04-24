import discord
from discord.ext import commands
from discord import app_commands
import os
import json
from colorama import init, Fore, Style
from flask import Flask
from threading import Thread

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

# წამოიღე ტოკენი გარემოდან
token = os.getenv("DISCORD_TOKEN")

if token:
    bot.run(token)
else:
    print("❌ Token not found. Please set the 'DISCORD_TOKEN' environment variable.")

app = Flask(__name__)


@app.route('/')
def home():
    return "Bot is alive!"


def run():
    app.run(host='0.0.0.0', port=8080)


def keep_alive():
    t = Thread(target=run)
    t.start()

keep_alive()

init(autoreset=True)


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
    async def spam_button(self, interaction: discord.Interaction,
                          button: discord.ui.Button):
        await interaction.response.defer()
        for _ in range(5):
            await interaction.followup.send(self.message)


@bot.tree.command(name="spamraid",
                  description="Send a message and generate a button to spam")
@app_commands.describe(message="The message you want to spam")
async def spamraid(interaction: discord.Interaction, message: str):
    view = SpamButton(message)
    await interaction.response.send_message(f"💥SPAM TEXT💥 : {message}",
                                            view=view,
                                            ephemeral=True)


@bot.event
async def on_ready():
    display_logo()
    display_status(True)
    print("Connected as " + Fore.YELLOW + f"{bot.user}")

    try:
        await bot.tree.sync()
        print(Fore.GREEN + "Commands successfully synchronized.")
    except Exception as e:
        display_status(False)
        print(Fore.RED + f"Error during synchronization: {e}")


if __name__ == "__main__":
    TOKEN = token_management()
    if TOKEN:
        try:
            bot.run(token)
        except discord.errors.LoginFailure:
            print(Fore.RED +
                  "Can't connect to token. Please check your token.")
            input(Fore.YELLOW + "Press Enter to go back to the menu...")
            TOKEN = token_management()  # Restart the token selection process
            if TOKEN:
                bot.run(token)  # Run again with the new token
        except Exception as e:
            print(Fore.RED + f"An unexpected error occurred: {e}")
            input(Fore.YELLOW + "Press Enter to restart the menu...")
            TOKEN = token_management()  # Restart the token selection process
            if TOKEN:
                bot.run(token)  # Run again with the new token
    else:
        print(Fore.RED + "❌ Error: Unable to load or set a token.")
