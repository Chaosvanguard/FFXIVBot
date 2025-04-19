import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Select
from config import *
from utils.ffxiv_data import *
import urllib.parse
import re

CRAFT_JOBS = {
    8: "Carpenter", 9: "Blacksmith", 10: "Armorer", 11: "Goldsmith",
    12: "Leatherworker", 13: "Weaver", 14: "Alchemist", 15: "Culinarian"
}

class RecipeSelect(Select):
    def __init__(self, item_data, craft_data, wiki_url, ingredient_cache):
        options = []
        for index, r in enumerate(craft_data):
            level = r.get("rlvl") or r.get("level") or "?"
            job = CRAFT_JOBS.get(r.get("job", 0), "Unknown")
            hq_desc = "HQ available" if r.get("hq") == 1 else "NQ only"
            options.append(discord.SelectOption(
                label=f"{job} (Level {level})",
                description=hq_desc,
                value=str(index)
            ))
        super().__init__(placeholder="Choose a recipe variant...", min_values=1, max_values=1, options=options)
        self.item_data = item_data
        self.craft_data = craft_data
        self.wiki_url = wiki_url
        self.ingredient_cache = ingredient_cache

    async def callback(self, interaction: discord.Interaction):
        index = int(self.values[0])
        recipe = self.craft_data[index]
        ingredient_lines = []

        for ing in recipe.get("ingredients", []):
            ing_id, ing_amount = ing["id"], ing["amount"]
            ing_name = self.ingredient_cache.get(ing_id, "Unknown")
            ingredient_lines.append(f"{ing_amount}x {ing_name}")

        icon_path = str(self.item_data.get("icon") or self.item_data.get("c", "")).strip()
        thumbnail_url = f"https://www.garlandtools.org/files/icons/item/{icon_path}.png" if icon_path else None
        stars = recipe.get("stars", 0)
        star_display = f" ⭐x{stars}" if stars else ""
        hq_note = "HQ craftable" if recipe.get("hq") == 1 else "NQ only"
        job_name = CRAFT_JOBS.get(recipe.get("job", 0), "Unknown")

        embed = discord.Embed(
            title=self.item_data.get("name") or self.item_data.get("n", "Unknown Item"),
            description=f"Crafted by: **{job_name}** (Level {recipe.get('rlvl', '?')}){star_display}",
            color=discord.Color.dark_gold()
        )
        embed.url = self.wiki_url
        embed.add_field(name="Ingredients", value="\n".join(ingredient_lines), inline=False)
        embed.add_field(name="Notes", value=hq_note, inline=True)
        if thumbnail_url:
            embed.set_thumbnail(url=thumbnail_url)
        embed.set_footer(text="📦 Data provided by Garland Tools")

        await interaction.response.edit_message(embed=embed, view=self.view)

class RecipeView(View):
    def __init__(self, item_data, craft_data, wiki_url, ingredient_cache):
        super().__init__()
        self.add_item(RecipeSelect(item_data, craft_data, wiki_url, ingredient_cache))

class CraftingRecipes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.ingredient_cache = {}

    @app_commands.command(name="recipe", description="Search for the recipe for an item.")
    async def recipe(self, interaction: discord.Interaction, item_name: str):
        await interaction.response.defer()
        item_name = re.sub(r'\s+', ' ', item_name.strip())
        wiki_url = f"https://ffxiv.consolegameswiki.com/wiki/{urllib.parse.quote(item_name.replace(' ', '_'))}"

        try:
            recipe_info = await get_recipe_details(item_name)
            source = recipe_info["source"]
            data = recipe_info["data"]

            if source == "xivapi":
                ingredients = []
                for i in range(10):
                    item_field = data.get(f"ItemIngredient{i}")
                    amount = data.get(f"AmountIngredient{i}")
                    if item_field and amount:
                        ingredients.append(f"{amount}x {item_field['Name']}")

                icon_url = data.get("IconHD") or data.get("Icon")
                embed = discord.Embed(
                    title=data['Name'],
                    description=f"Crafted by: **{data['ClassJob']['Name']}** (Level {data['RecipeLevelTable']['ClassJobLevel']})",
                    color=discord.Color.blurple()
                )
                embed.url = wiki_url
                embed.add_field(name="Ingredients", value="\n".join(ingredients), inline=False)
                embed.set_footer(text="Data provided by XIVAPI")
                if icon_url:
                    embed.set_thumbnail(url=f"https://xivapi.com/{icon_url}")
                await interaction.followup.send(embed=embed)

            elif source == "garlandtools":
                item_data = data.get("item", {}) or recipe_info.get("item_data", {})
                craft_data = item_data.get("craft", [])
                async with aiohttp.ClientSession() as session:
                    for ing in craft_data:
                        for entry in ing.get("ingredients", []):
                            ing_id = entry["id"]
                            if ing_id not in self.ingredient_cache:
                                url = f"https://www.garlandtools.org/db/doc/item/en/3/{ing_id}.json"
                                try:
                                    data = await fetch_json(session, url)
                                    self.ingredient_cache[ing_id] = data.get("item", {}).get("name", "Unknown")
                                except Exception as e:
                                    print(f"[WARN] Failed to fetch ingredient {ing_id}: {e}")
                                    self.ingredient_cache[ing_id] = "Unknown"

                if len(craft_data) > 1:
                    view = RecipeView(item_data, craft_data, wiki_url, self.ingredient_cache)
                    return await interaction.followup.send(content="🔽 Multiple recipes found. Choose one:", view=view)

                # fallback to showing the first recipe
                recipe = craft_data[0]
                ingredient_lines = [
                    f"{ing['amount']}x {self.ingredient_cache.get(ing['id'], 'Unknown')}"
                    for ing in recipe.get("ingredients", [])
                ]

                icon_raw = str(item_data.get("icon") or item_data.get("c", "")).strip()
                thumbnail_url = f"https://www.garlandtools.org/files/icons/item/{icon_raw}.png" if icon_raw else None
                stars = recipe.get("stars", 0)
                hq_note = "HQ craftable" if recipe.get("hq") == 1 else "NQ Only"
                job_name = CRAFT_JOBS.get(recipe.get("job", 0), "Unknown")
                embed = discord.Embed(
                    title=item_data.get("name") or item_data.get("n", "Unknown Item"),
                    description=f"Crafted by: **{job_name}** (Level {recipe.get('rlvl', '?')}) {'⭐x' + str(stars) if stars else ''}",
                    color=discord.Color.dark_gold()
                )
                embed.url = wiki_url
                embed.add_field(name="Ingredients", value="\n".join(ingredient_lines), inline=False)
                embed.add_field(name="Notes", value=hq_note, inline=True)
                embed.set_footer(text="📦 Data provided by Garland Tools")
                if thumbnail_url:
                    embed.set_thumbnail(url=thumbnail_url)
                await interaction.followup.send(embed=embed)

        except Exception as e:
            print(f"[ERROR] Recipe fetch failed: {type(e).__name__}: {e}")
            await interaction.followup.send("❌ Failed to retrieve recipe information.")

async def setup(bot):
    await bot.add_cog(CraftingRecipes(bot))