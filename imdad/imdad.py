import re

import discord
from redbot.core import commands, Config
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import escape


class ImDad:
    """Bonus points if you post something from this cog on r/discord_irl"""
    DAD_REGEX = re.compile(r"^I'?m (?P<TEXT>.+)+$", re.IGNORECASE)

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1923523124, force_registration=True)
        self.config.register_guild(enabled=False, name="{me.name}")

    @commands.group(invoke_without_command=True)
    async def imdad(self, ctx: commands.Context):
        """Toggle High Quality Dad Jokes(tm)"""
        new_setting = not await self.config.guild(ctx.guild).enabled()
        await self.config.guild(ctx.guild).enabled.set(new_setting)
        await ctx.send(
            f"High Quality Dad Jokes\N{TRADE MARK SIGN} are now"
            f" {'enabled' if new_setting is True else 'disabled'}."
        )

    @imdad.command()
    async def name(self, ctx: commands.Context, *, name: str = None):
        """Set the name used for the response"""
        name = name if name is not None else "{me.name}"
        await self.config.guild(ctx.guild).name.set(name)
        await ctx.send(f"Set name to {escape(name, mass_mentions=True)}")

    async def on_message(self, message: discord.Message):
        if not message.guild or not message.channel.permissions_for(message.guild.me).send_messages:
            return
        if not await self.config.guild(message.guild).enabled():
            return
        match = self.DAD_REGEX.match(message.content)
        if match is None:
            return
        name = escape(
            (await self.config.guild(message.guild).name()).format(
                me=self.bot.user, author=message.author
            ),
            mass_mentions=True,
        )
        await message.channel.send(
            f"Hi {escape(match.group('TEXT'), mass_mentions=True)}, I'm {name}!"
        )
