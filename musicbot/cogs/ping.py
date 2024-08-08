import time
import discord
from discord import app_commands
from discord.ext import commands
from musicbot import LOGGER, BOT_NAME_TAG_VER, COLOR_CODE


class Ping(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Measure ping speed")
    async def ping(self, interaction: discord.Interaction):
        latency = self.bot.latency
        before = time.monotonic()
        embed = discord.Embed(
            title="**Ping**",
            description=f"🏓 Pong! WebSocket Ping {round(latency * 1000)}ms\n🏓 Pong! Measuring...",
            color=COLOR_CODE,
        )
        embed.set_footer(text=BOT_NAME_TAG_VER)
        await interaction.response.send_message(embed=embed)

        ping = (time.monotonic() - before) * 1000
        embed = discord.Embed(
            title="**Ping**",
            description=f"🏓 Pong! WebSocket Ping {round(latency * 1000)}ms\n🏓 Pong! Message Ping {int(ping)}ms",
            color=COLOR_CODE,
        )
        embed.set_footer(text=BOT_NAME_TAG_VER)
        await interaction.edit_original_response(embed=embed)


async def setup(bot):
    await bot.add_cog(Ping(bot))
    LOGGER.info("Ping loaded!")
