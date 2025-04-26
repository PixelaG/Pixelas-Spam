import json
import re
import os
import time
import discord
import asyncio
from discord.ext import commands, tasks
from discord import app_commands
from flask import Flask
from threading import Thread
from colorama import init, Fore
from datetime import datetime, timedelta
from pymongo import MongoClient

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
    thread.daemon = True
    thread.start()


keep_alive()

# MongoDB setup
MONGO_URI = os.getenv("MONGO_URI")
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["discord_bot"]
role_expiry_collection = db["role_expiries"]


# Constants
BUYER_ROLE_ID = 1365076710265192590
LOG_CHANNEL_ID = 1365381000619622460  # შეცვალე შენი არხით


# MongoDB role expiry handlers
def load_expiries():
    expiries = {}
    print(f"🔍 Accessing role_expiry_collection...")
    for doc in role_expiry_collection.find():
        print(f"Found expiry for user: {doc['user_id']}")
        user_id = str(doc["user_id"])
        expiries[user_id] = {
            "guild_id": doc["guild_id"],
            "role_id": doc["role_id"],
            "expires_at": doc["expires_at"]
        }
    return expiries

def save_expiry(user_id, data):
    collection.update_one({"user_id": int(user_id)}, {"$set": data}, upsert=True)

def delete_expiry(user_id):
    collection.delete_one({"user_id": int(user_id)})


role_expiries = load_expiries()

# Discord bot setup
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.typing = False
intents.presences = False

bot = commands.Bot(command_prefix="!", intents=intents)


# Universal embed notification
async def send_embed_notification(interaction,
                                  title,
                                  description,
                                  color=discord.Color(0x2f3136)):
    embed = discord.Embed(title=title, description=description, color=color)
    try:
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed,
                                                    ephemeral=True)
    except discord.NotFound:
        print("⚠ Interaction უკვე ამოიწურა ან გაუქმდა.")
    except discord.HTTPException as e:
        print(f"⚠ HTTP შეცდომა Embed-ის გაგზავნისას: {e}")


# Helper: Check permissions
async def check_user_permissions(interaction, required_role_id: int,
                                 guild_id: int):
    home_guild = discord.utils.get(bot.guilds, id=guild_id)
    if not home_guild:
        await send_embed_notification(interaction,
                                      "⚠️ მთავარი სერვერი არ არის ნაპოვნი",
                                      "⌚️ სცადეთ მოგვიანებით.")
        return None

    try:
        member = await home_guild.fetch_member(interaction.user.id)
    except discord.NotFound:
        await send_embed_notification(
            interaction, "⛔️ თქვენ არ ხართ მთავარ სერვერზე",
            "🌐 შემოგვიერთდით ახლავე [Server](https://discord.gg/byScSM6T9Q)")
        return None

    if not any(role.id == required_role_id for role in member.roles):
        await send_embed_notification(
            interaction, "🚫 თქვენ არ შეგიძლიათ ამ ფუნქციის გამოყენება",
            "💸 შესაძენად ეწვიეთ სერვერს [Server](https://discord.gg/byScSM6T9Q) 💸"
        )
        return None

    return member


# Cooldown dictionary
cooldowns = {}


def dm_cooldown(seconds: int):

    def predicate(interaction: discord.Interaction):
        now = time.time()
        user_id = interaction.user.id
        last_used = cooldowns.get(user_id, 0)

        if now - last_used < seconds:
            remaining = int(seconds - (now - last_used))
            raise app_commands.CheckFailure(
                f"გთხოვთ დაელოდოთ {remaining} წამს ბრძანების ხელახლა გამოსაყენებლად."
            )

        cooldowns[user_id] = now
        return True

    return app_commands.check(predicate)


# Spam button
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


# Single-use button
class SingleUseButton(discord.ui.View):

    def __init__(self, message):
        super().__init__()
        self.message = message
        self.sent = False

    @discord.ui.button(label="გაგზავნა", style=discord.ButtonStyle.green)
    async def send_once(self, interaction: discord.Interaction,
                        button: discord.ui.Button):
        if self.sent:
            await interaction.response.send_message("⛔ უკვე გაგზავნილია!",
                                                    ephemeral=True)
            return

        self.sent = True
        button.disabled = True

        await interaction.response.defer()
        await interaction.followup.send(self.message)

        try:
            original_message = await interaction.original_response()
            await original_message.edit(view=self)
        except discord.NotFound:
            print(
                "⚠ ვერ მოხერხდა ღილაკის რედაქტირება — შეტყობინება აღარ არსებობს."
            )


# Time parsing function
def parse_duration(duration_str):
    time_units = {'d': 86400, 'h': 3600, 'm': 60}
    total_seconds = 0
    matches = re.findall(r'(\d+)([dhm])', duration_str.lower())
    for value, unit in matches:
        if unit in time_units:
            total_seconds += int(value) * time_units[unit]
    return total_seconds


@tasks.loop(minutes=1)
async def check_expired_roles():
    await bot.wait_until_ready()

    guild = bot.get_guild(1005186618031869952)
    if not guild:
        return

    now = datetime.utcnow()

    # Create the list to hold the user IDs of expired users
    to_remove = []

    # Find expired roles
    expired_users = role_expiry_collection.find({"expires_at": {"$lte": now}})

    for user_data in expired_users:
        user_id = int(user_data["user_id"])
        try:
            member = await guild.fetch_member(user_id)
        except discord.NotFound:
            continue

        role = guild.get_role(BUYER_ROLE_ID)
        if role in member.roles:
            try:
                await member.remove_roles(role)
                print(f"✅ {member.display_name}-ს წაეშალა მყიდველის როლი.")
            except discord.Forbidden:
                print(f"⛔ ვერ მოვხსენით როლი {member.display_name}-ს – არ გვაქვს შესაბამისი უფლებები.")
            except Exception as e:
                print(f"❌ შეცდომა {member.display_name}-სთან მუშაობისას: {e}")

        # Add user ID to the to_remove list
        to_remove.append(str(user_id))  # Append as string to match the format in role_expiries

    # After processing expired roles, delete them from the database
    for user_id in to_remove:
        role_expiry_collection.delete_one({"user_id": user_id})
        del role_expiries[user_id]  # Remove from the in-memory dictionary as well
        save_expiries(role_expiries)  # Ensure the updated expiries are saved


@bot.command(name="buy")
@commands.has_permissions(manage_roles=True)
async def buy(ctx, member: discord.Member, duration: str = "30d"):
    role = discord.utils.get(ctx.guild.roles, id=BUYER_ROLE_ID)
    if not role:
        await ctx.send("❌ ვერ ვიპოვე მყიდველის როლი.")
        return

    seconds = parse_duration(duration)
    if seconds <= 0:
        await ctx.send("⛔️ შეცდომა : არასწორი დროის ფორმატი. გამოიყენე მაგ: `14d`, `5h`, `30m`")
        return

    try:
        await member.add_roles(role, reason=f"გადახდა: {duration}")
        expires_at = datetime.utcnow() + timedelta(seconds=seconds)

        save_expiry(member.id, {
            "user_id": member.id,
            "guild_id": ctx.guild.id,
            "role_id": BUYER_ROLE_ID,
            "expires_at": expires_at.isoformat()
        })

        log_channel = ctx.guild.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(
                f"# 💰 {member.mention}-ს მიენიჭა **მყიდველის როლი** {duration}-ით\n📅 ვადა: {expires_at}")

        await ctx.send(f"# 🟢 როლი მიენიჭა {member.mention}-ს {duration}-ით.")
    except Exception as e:
        await ctx.send(f"⛔️ შეცდომა : {e}")

# Command to check role expiry
@bot.command(name="check")
@commands.has_permissions(administrator=True)
async def check_role(ctx, member: discord.Member = None):
    if member is None:
        await ctx.send(
            "# ⛔️ შეცდომა : გთხოვთ მიუთითოთ მომხმარებელი, რომლის როლსაც ამოწმებთ. "
            "გამოიყენეთ ბრძანება ასე: `!check @user`.")
        return

    data = role_expiries.get(str(member.id))
    if not data:
        await ctx.send(f"# ℹ️ {member.display_name}-ს არ აქვს აქტიური სერვისი."
                       )
        return

    expires_at = data.get("expires_at")

    # დარწმუნდით რომ expires_at არის datetime ობიექტი, თუ არა, გადააკეთეთ
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(
            expires_at)  # ISO 8601 ფორმატიდან datetime-ში
    if isinstance(expires_at, datetime):
        expires_at = int(
            expires_at.timestamp())  # datetime-დან timestamp-ში გადავყავთ

    now = int(time.time())

    if now >= expires_at:
        await ctx.send(f"❌ {member.display_name}-ს როლი უკვე ვადაგასულია.")
        return

    remaining = expires_at - now
    days = remaining // 86400
    hours = (remaining % 86400) // 3600
    minutes = (remaining % 3600) // 60

    await ctx.send(
        f"📋 {member.mention}-ს **მყიდველის როლი** მოქმედებს\n"
        f"⏳ დარჩენილი დრო: {days} დღე, {hours} საათი, {minutes} წუთი\n"
        f"📅 იწურება: <t:{expires_at}:F>")


# /spamraid command
@app_commands.describe(message="The message you want to spam")
@bot.tree.command(
    name="spamraid",
    description="გაგზავნეთ შეტყობინება და შექმენით ღილაკი სპამისთვის")
async def spamraid(interaction: discord.Interaction, message: str):
    await bot.wait_until_ready()

    member = await check_user_permissions(interaction, 1365076710265192590,
                                          1005186618031869952)
    if not member:
        return

    embed = discord.Embed(title="💥 გასასპამი ტექსტი 💥",
                          description=message,
                          color=discord.Color(0x2f3136))
    embed.set_footer(text=f"შექმნილია {interaction.user.display_name}")

    view = SpamButton(message)
    try:
        await interaction.response.send_message(embed=embed,
                                                view=view,
                                                ephemeral=True)
    except discord.NotFound:
        print("⚠ Interaction ვადა გასულია (spamraid).")


# /onlyone command
@app_commands.describe(message="შეტყობინება რაც გინდა რომ გაგზავნოს ერთხელ")
@bot.tree.command(name="onlyone",
                  description="მხოლოდ ერთხელ გაგზავნის ღილაკით შეტყობინებას")
async def onlyone(interaction: discord.Interaction, message: str):
    await bot.wait_until_ready()

    member = await check_user_permissions(interaction, 1365076710265192590,
                                          1005186618031869952)
    if not member:
        return

    embed = discord.Embed(title="🟢 ერთჯერადი გაგზავნის ღილაკი",
                          description=message,
                          color=discord.Color.green())
    embed.set_footer(text=f"შექმნილია {interaction.user.display_name}")

    view = SingleUseButton(message)
    try:
        await interaction.response.send_message(embed=embed,
                                                view=view,
                                                ephemeral=True)
    except discord.NotFound:
        print("⚠ Interaction ვადა გასულია (onlyone).")


# /dmmsg command with cooldown
@bot.tree.command(name="dmmsg", description="გაგზავნე DM არჩეულ მომხმარებელზე")
@app_commands.describe(user="მომხმარებელი, რომელსაც გსურს პირადში მიწერა",
                       message="შეტყობინება რომელიც გსურს რომ გააგზავნო")
async def dmmsg(interaction: discord.Interaction, user: discord.User,
                message: str):
    await bot.wait_until_ready()

    # Cooldown შემოწმება
    seconds = 300  # 5 წუთი
    user_id = interaction.user.id
    now = time.time()
    last_used = cooldowns.get(user_id, 0)

    if now - last_used < seconds:
        remaining = int(seconds - (now - last_used))
        await send_embed_notification(
            interaction, "⏱ Cooldown აქტიურია",
            f"გთხოვთ დაელოდოთ {remaining} წამს ბრძანების ხელახლა გამოსაყენებლად."
        )
        return

    # უფლებების შემოწმება
    member = await check_user_permissions(interaction, 1365076710265192590,
                                          1005186618031869952)
    if not member:
        return

    try:
        await user.send(message)
        cooldowns[
            user_id] = now  # ✅ მხოლოდ წარმატების შემთხვევაში ვანახლებთ cooldown-ს
        await send_embed_notification(interaction, "✅ შეტყობინება გაგზავნილია",
                                      f"{user.mention}-ს მივწერეთ პირადში.")
    except discord.Forbidden:
        await send_embed_notification(
            interaction, "🚫 ვერ მოხერხდა გაგზავნა",
            f"{user.mention} არ იღებს პირად შეტყობინებებს.")
    except discord.HTTPException as e:
        await send_embed_notification(interaction,
                                      "❌ შეცდომა შეტყობინების გაგზავნისას",
                                      f"დეტალები: {e}")


# Bot ready
@bot.event
async def on_ready():
    print(f"✅ Bot connected as {bot.user}")
    check_expired_roles.start()
    await bot.change_presence(status=discord.Status.invisible)
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
