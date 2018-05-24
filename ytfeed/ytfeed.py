import asyncio
from datetime import datetime
from typing import List

import discord
from redbot.core import commands, checks
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import escape

from cog_shared.swift_libs import cmd_help, PaginatedMenu, tick
from .feeds import Feed, log
from .config import config, i18n


class YTFeed:

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = config
        self._feed_task = self.bot.loop.create_task(self.rss_task())

    # noinspection PyMethodMayBeStatic
    def __unload(self):
        self._feed_task.cancel()
        from .feeds import session

        session.close()

    async def rss_task(self):
        await self.bot.wait_until_ready()
        while True:
            async for feed in Feed.all_feeds():
                channels: List[discord.TextChannel] = [
                    x for x in [self.bot.get_channel(x) for x in await feed.conf.channels()] if x
                ]
                if not channels:
                    continue

                try:
                    feed_data = await feed.resolve()
                except RuntimeError:
                    continue

                last_video = datetime.fromtimestamp(await feed.conf.last_video())
                videos = list(filter(lambda x: x.timestamp > last_video, feed_data["videos"]))[:5]

                log.debug(f"{len(videos)} videos")

                if videos:
                    await feed.conf.last_video.set(max(x.timestamp.timestamp() for x in videos))
                else:
                    continue

                for video in videos:
                    for channel in channels:
                        if not channel:
                            continue
                        guild = channel.guild
                        if not channel.permissions_for(guild.me).send_messages:
                            continue

                        message_content = await self.config.guild(guild).message()
                        await channel.send(
                            content=message_content.format(channel=video.channel, video=video),
                            embed=video.embed(colour=guild.me.colour),
                        )

            await asyncio.sleep(5 * 60)

    @commands.group()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_channels=True)
    async def ytfeed(self, ctx: commands.Context):
        """Manage YouTube feed subscriptions"""
        await cmd_help(ctx)

    @ytfeed.command(name="add")
    async def add_feed(self, ctx: commands.Context, cid: str, channel: discord.TextChannel = None):
        """Follow a YouTube channel's feed

        The channel ID must be used (not a custom channel URL or the channel name!)
        """
        feed = Feed(cid)
        try:
            data = await feed.resolve()
        except RuntimeError:
            await ctx.send(
                i18n(
                    "Failed to validate the given channel ID"
                    " (did you accidentally use the channel URL instead?)"
                )
            )
            return

        cid = getattr(channel, "id", ctx.channel.id)
        async with feed.conf() as feed_conf:
            if "channels" not in feed_conf:
                feed_conf["channels"] = []

            if cid in feed_conf["channels"]:
                await ctx.send(i18n("The given channel is already setup to follow that channel"))
                return

            if not feed_conf["channels"]:
                # avoid posting all videos from the channel when we do the next feed poll
                feed_conf["last_video"] = datetime.utcnow().timestamp()

            feed_conf["channels"].append(cid)
        await ctx.send(
            tick(i18n("Now following uploads from {channel}").format(channel=data["channel"].name))
        )

    @ytfeed.command(name="remove")
    async def remove_feed(
        self, ctx: commands.Context, cid: str, channel: discord.TextChannel = None
    ):
        """Unfollow a YouTube channel's feed"""
        feed = Feed(cid)
        try:
            data = await feed.resolve()
        except RuntimeError:
            await ctx.send(
                i18n(
                    "Failed to validate the given channel ID"
                    " (did you accidentally use the channel URL instead?)"
                )
            )
            return

        async with feed.conf.channels() as channels:
            if cid not in channels:
                await ctx.send(i18n("The given channel is not setup to follow that channel"))
                return

            channels.remove(getattr(channel, "id", ctx.channel.id))
        await ctx.send(
            tick(
                i18n("No longer following uploads from {channel}").format(
                    channel=data["channel"].name
                )
            )
        )

    @ytfeed.command(name="message")
    async def upload_message(self, ctx: commands.Context, *, message: str = None):
        """Set the message to be used for new uploads

        Available placeholders:
        `{channel}`, `{video}`
        """
        if message is None:
            message = config.guild(ctx.guild).message.default
        await config.guild(ctx.guild).message.set(message)
        await ctx.send(
            tick(
                i18n("Set upload message to `{}`").format(
                    escape(message, mass_mentions=True, formatting=True)
                )
            )
        )

    @ytfeed.command(hidden=True)
    async def videos(self, ctx: commands.Context, cid: str):
        data = await Feed(cid).resolve()
        await PaginatedMenu(
            pages=data["videos"],
            ctx=ctx,
            converter=lambda x: (f"Video {x.current} / {x.total}", x.data.embed()),
        )
