import os
import sqlite3
from contextlib import closing
from musicbot.config import Development as Config
import discord
from discord import app_commands
from discord.ext import commands

from musicbot.utils.language import get_lan
from musicbot import LOGGER, BOT_NAME_TAG_VER, COLOR_CODE

lan_pack = [
    file.replace(".json", "")
    for file in os.listdir("musicbot/languages")
    if file.endswith(".json")
]


class Language(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.userdata_table = "language"

    @app_commands.command(name="language", description="Apply the language pack.")
    @app_commands.choices(
        lang=[app_commands.Choice(name=lang, value=lang) for lang in lan_pack]
    )
    async def language(self, interaction: discord.Interaction, lang: str = None):
        if lang is None:
            files = "\n".join(lan_pack)
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "set_language_pack_list"),
                description=files,
                color=COLOR_CODE,
            )
            embed.set_footer(text=BOT_NAME_TAG_VER)
            return await interaction.response.send_message(embed=embed)

        if lang not in lan_pack:
            embed = discord.Embed(
                title=get_lan(interaction.user.id, "set_language_pack_not_exist"),
                color=COLOR_CODE,
            )
            embed.set_footer(text=BOT_NAME_TAG_VER)
            return await interaction.response.send_message(embed=embed)

        with closing(sqlite3.connect(Config.DB_PATH)) as conn:
            with closing(conn.cursor()) as cursor:
                cursor.execute(
                    f"""
                    SELECT * FROM {self.userdata_table} WHERE id=?
                    """,
                    (str(interaction.user.id),),
                )
                a = cursor.fetchone()
                if a is None:
                    cursor.execute(
                        f"""
                        INSERT INTO {self.userdata_table} VALUES(?, ?)
                        """,
                        (str(interaction.user.id), lang),
                    )
                    embed = discord.Embed(
                        title=get_lan(interaction.user.id, "set_language_complete"),
                        description=f"{lang}",
                        color=COLOR_CODE,
                    )
                else:
                    cursor.execute(
                        f"""
                        UPDATE {self.userdata_table} SET language=? WHERE id=?
                        """,
                        (lang, str(interaction.user.id)),
                    )
                    embed = discord.Embed(
                        title=get_lan(interaction.user.id, "set_language_complete"),
                        description=f"{a[1]} --> {lang}",
                        color=COLOR_CODE,
                    )
                conn.commit()

        embed.set_footer(text=BOT_NAME_TAG_VER)
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Language(bot))
    LOGGER.info("Language loaded!")
