import discord
from discord import app_commands
import requests
import os
from dotenv import load_dotenv
import math

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
BS_API_KEY = os.getenv("BRAWL_API_KEY")

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
HEADERS = {"Authorization": f"Bearer {BS_API_KEY}"}

def get_profile(player_tag: str):
    tag_encoded = player_tag.upper().replace("#", "%23")
    url = f"https://api.brawlstars.com/v1/players/{tag_encoded}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        return None, f"API Error: {response.status_code}"
    return response.json(), None

class BrawlerEmbedView(discord.ui.View):
    def __init__(self, profile_data, brawlers):
        super().__init__(timeout=180)
        self.profile_data = profile_data
        # Sort brawlers descending by trophies
        self.brawlers = sorted(brawlers, key=lambda b: b.get('trophies',0), reverse=True)
        self.page = 0
        self.per_page = 18
        self.max_page = max(0, math.ceil(len(self.brawlers) / self.per_page) - 1)

    def get_embed(self):
        start = self.page * self.per_page
        end = start + self.per_page
        page_brawlers = self.brawlers[start:end]

        # Additional info
        club_name = self.profile_data.get("club", {}).get("name", "No club")
        wins_3v3 = self.profile_data.get("3vs3Victories", 0)
        wins_showdown = self.profile_data.get("soloVictories", 0) + self.profile_data.get("duoVictories", 0)
        

        embed = discord.Embed(
            title=f"{self.profile_data['name']} ({self.profile_data['tag']})",
            description=(
                f"Trophies: {self.profile_data.get('trophies',0)} | Level: {self.profile_data.get('expLevel',0)}\n"
                f"Club: {club_name}\n"
                f"3v3 Wins: {wins_3v3} | Showdown Wins: {wins_showdown}"
            ),
            color=discord.Color.gold()
        )
        embed.set_footer(text=f"Page {self.page + 1}/{self.max_page + 1}")

        # Thumbnail: first brawler's icon
        if page_brawlers:
            first_icon_url = f"https://cdn.brawlstats.com/brawlers/{page_brawlers[0]['id']}.png"
            embed.set_thumbnail(url=first_icon_url)

        # Add brawlers (name + trophies + level)
        value = ""
        for b in page_brawlers:
            value += f"**{b['name']}** - {b['trophies']} 🏆 (Power {b['power']})\n"
        embed.add_field(name="Unlocked Brawlers", value=value, inline=False)
        return embed

    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.primary)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1
            await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="➡️", style=discord.ButtonStyle.primary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page < self.max_page:
            self.page += 1
            await interaction.response.edit_message(embed=self.get_embed(), view=self)

@tree.command(name="profile", description="Display a Brawl Stars player's profile")
@app_commands.describe(tag="Brawl Stars player tag (e.g. #PY9J8Q)")
async def profile(interaction: discord.Interaction, tag: str):
    await interaction.response.defer()
    data, error = get_profile(tag)
    if error:
        await interaction.followup.send(f"❌ {error}")
        return
    if not data:
        await interaction.followup.send("❌ Profile not found.")
        return

    brawlers = [b for b in data.get("brawlers", []) if b.get("power", 0) > 0 or b.get("trophies", 0) > 0]
    if not brawlers:
        await interaction.followup.send("❌ No brawlers unlocked.")
        return

    view = BrawlerEmbedView(data, brawlers)
    await interaction.followup.send(embed=view.get_embed(), view=view)

@client.event
async def on_ready():
    await tree.sync()
    print(f"✅ Logged in as {client.user}")

client.run(DISCORD_TOKEN)
