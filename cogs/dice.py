import discord
from discord import app_commands
from discord.ext import commands
import random

class Dice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="roll", description="Roll a dice in NdX format (e.g. 2d20)")
    async def roll(self, interaction: discord.Interaction, dice: str = "1d20"):
        try:
            rolls, total = self.parse_dice(dice)
            await interaction.response.send_message(f"🎲 Rolled `{dice}`: {rolls} → **{total}**")
        except Exception as e:
            await interaction.response.send_message(f"Error: {str(e)}")

    def parse_dice(self, dice_str):
        rolls = []
        num, die = map(int, dice_str.lower().split("d"))
        for _ in range(num):
            rolls.append(random.randint(1, die))
        return rolls, sum(rolls)

async def setup(bot):
    await bot.add_cog(Dice(bot))