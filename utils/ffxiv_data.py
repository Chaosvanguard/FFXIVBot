import aiohttp
import urllib.parse
import re
from config import *

async def fetch_json(session, url, params=None):
    async with session.get(url, params=params) as resp:
        if resp.status != 200:
            raise ValueError(f"Failed to fetch: {url}")
        return await resp.json()
    
async def search_item(item_name):
    item_name = re.sub(r'\s+', ' ', item_name.strip())
    item_name_cleaned = re.sub(r"[’'\".,\-]", "", item_name).lower()

    async with aiohttp.ClientSession() as session:
        search_url = f"https://garlandtools.org/api/search.php?text={urllib.parse.quote(item_name)}"
        search_data = await fetch_json(session, search_url)
        matches = [entry for entry in search_data if entry.get("type") == "item"]
        print("[DEBUG] GarlandTool search matches:", [m.get("obj", {}).get("n", "") for m in matches])
        match = next((m for m in matches if re.sub(r"[’'\".,\-]", "", m.get("obj", {}).get("n", "").lower()) == item_name_cleaned), None)
        if not match:
            match = next((m for m in matches if item_name_cleaned in re.sub(r"[’'\".,\-]", "", m.get("obj", {}).get("n", "").lower())), None)
        if not match or "id" not in match:
            raise ValueError("No valid item match found in Garland Tools.")

        item_id = int(match["id"])
        return item_id, match.get("obj", {})
    
async def fetch_recipe_xiv(item_id):
    async with aiohttp.ClientSession() as session:
        base_params = {"private_key": XIVAPI_KEY}
        params = {**base_params, "filters": f"ItemResult.ID={item_id}"}
        search_resp = await fetch_json(session, f"https://xivapi.com/recipe", params=params)
        recipes = [r for r in search_resp.get("Results", []) if r.get("ItemResult", {}).get("ID") == item_id]
        if not recipes:
            raise ValueError("No matching recipe found in XIVAPI.")
        recipe_id = recipes[0]['ID']
        recipe_details = await fetch_json(session, f"https://xivapi.com/recipe/{recipe_id}", base_params)
        return recipe_details
    
async def fetch_recipe_garland(item_id):
    item_url = f"https://www.garlandtools.org/db/doc/item/en/3/{item_id}.json"
    async with aiohttp.ClientSession() as session:
        item_data = await fetch_json(session, item_url)
        return item_data
    
async def get_recipe_details(item_name):
    try:
        item_id, item_data = await search_item(item_name)
        try:
            recipe = await fetch_recipe_xiv(item_id)
            return {"source": "xivapi", "data": recipe}
        except Exception as e:
            print(f"XIVAPI failed: {e}, trying Garland Tools fallback...")
            recipe = await fetch_recipe_garland(item_id)
            return {"source": "garlandtools", "data": recipe, "item_data": item_data}
    except Exception as e:
        print(f"[search_item ERROR] {type(e).__name__}: {e}")
        raise