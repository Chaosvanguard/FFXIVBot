from discord.ext import commands
import json
from pathlib import Path

DATA_FILE = Path("data/profiles.json")

class Profiles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.profiles = self.load_profiles()

    def load_profiles(self):
        if DATA_FILE.exists():
            with open(DATA_FILE) as f:
                return json.load(f)
        return {}

    def save_profiles(self):
        with open(DATA_FILE, "w") as f:
            json.dump(self.profiles, f, indent=4)

    @commands.command(name="profile")
    async def profile(self, ctx, name: str = None, *, bio: str = None):
        user_id = str(ctx.author.id)
        if name and bio:
            self.profiles[user_id] = {"name": name, "bio": bio}
            self.save_profiles()
            await ctx.send(f"📘 Profile for **{name}** saved.")
        elif user_id in self.profiles:
            p = self.profiles[user_id]
            await ctx.send(f"📖 **{p['name']}**: {p['bio']}")
        else:
            await ctx.send("No profile found. Use `!profile <name> <bio>` to create one.")

async def setup(bot):
    await bot.add_cog(Profiles(bot))
