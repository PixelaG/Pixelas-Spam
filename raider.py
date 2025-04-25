import os
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


# Start Flask in a separate thread
def keep_alive():
    thread = Thread(target=run_flask)
    thread.daemon = True
    thread.start()


keep_alive()

# Discord bot setup
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True  # Required for reading messages
intents.typing = False
intents.presences = False

bot = commands.Bot(command_prefix="!", intents=intents)


# Function to send embed notification
async def send_embed_notification(interaction,
                                  title,
                                  description,
                                  color=discord.Color(0x2f3136)):
    embed = discord.Embed(title=title, description=description, color=color)
    await interaction.response.send_message(embed=embed, ephemeral=True)


# SpamButton class for the spam button
class SpamButton(discord.ui.View):

    def __init__(self, message):
        super().__init__()
        self.message = message

    @discord.ui.button(label="გასპამვა", style=discord.ButtonStyle.red)
    async def spam_button(self, interaction: discord.Interaction,
                          button: discord.ui.Button):
        await interaction.response.defer()
        for _ in range(5):
            await interaction.followup.send(self.message)


# Slash command for spamraid
@app_commands.describe(message="The message you want to spam")
@bot.tree.command(
    name="spamraid",
    description="გაგზავნეთ შეტყობინება და შექმენით ღილაკი სპამისთვის")
async def spamraid(interaction: discord.Interaction, message: str):
    await bot.wait_until_ready()

    # Main server check
    home_guild = discord.utils.get(
        bot.guilds, id=1005186618031869952)  # replace with your server ID
    if not home_guild:
        await send_embed_notification(interaction,
                                      "⚠️ მთავარი სერვერი არ არის ნაპოვნი",
                                      "⌚️ სცადეთ მოგვიანებით.")
        return

    try:
        member = await home_guild.fetch_member(interaction.user.id)
    except discord.NotFound:
        await send_embed_notification(interaction,
                                      "⛔️ თქვენ არ ხართ მთავარ სერვერზე",
                                      "🌐 შემოგვიერთდით ახლავე [Server](https://discord.gg/byScSM6T9Q)")
        return

    if not any(role.id == 1365076710265192590
               for role in member.roles):  # replace with your role ID
        await send_embed_notification(
            interaction, "🚫 თქვენ არ შეგიძლიათ ამ ფუნქციის გამოყენება",
            "💸 შესაძენად ეწვიეთ სერვერს [Server](https://discord.gg/byScSM6T9Q) 💸"
        )
        return

    # Embed message for spamraid
    embed = discord.Embed(
        title="💥 გასასპამი ტექსტი 💥",
        description=message,
        color=discord.Color(0x2f3136)  # change color if needed
    )
    embed.set_footer(text=f"შექმნილია {interaction.user.display_name}")

    # Send the embed message
    view = SpamButton(message)
    await interaction.response.send_message(embed=embed,
                                            view=view,
                                            ephemeral=True)


# Event when bot is ready
@bot.event
async def on_ready():
    print(f"✅ Bot connected as {bot.user}")
    await bot.change_presence(status=discord.Status.invisible)
    try:
        await bot.tree.sync()
        print(Fore.GREEN + "✅ Slash commands synced successfully.")
    except Exception as e:
        print(Fore.RED + f"❌ Failed to sync commands: {e}")


# Main execution
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print(Fore.RED + "❌ DISCORD_TOKEN environment variable is not set.")
