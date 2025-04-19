import discord
from discord.ext import commands
from discord import app_commands
import config

class Client(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
        self.initial_extensions = [
            "cogs.dice",
            "cogs.profiles",
            "cogs.recipes"
        ]
        self.synced_command = None

    async def setup_hook(self):
        for ext in self.initial_extensions:
            await self.load_extension(ext)

        self.synced_command = await self.tree.sync()

bot = Client()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} ({bot.user.id})")
    if bot.synced_command:
        print(f"Synced {len(bot.synced_command)} commands.")
    else:
        print(f"Slash commands not synced!")

bot.run(config.BOT_TOKEN)
