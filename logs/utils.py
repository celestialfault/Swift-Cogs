from asyncio import iscoroutinefunction

from redbot.core.config import Config, Value
from discord.abc import GuildChannel, Messageable
from discord import Guild, TextChannel, Member


async def toggle_setting(setting: Value, toggle: bool = None):
    """
    Toggles a specific Value object, optionally to a specific bool value
    """
    toggle = toggle if toggle is not None else not await setting()
    await setting.set(toggle)
    return toggle


async def validate_log_channel(channel: GuildChannel, guild: Guild) -> bool:
    """
    Checks to validate a log channel
    """
    if channel is None:
        return True
    return isinstance(channel, TextChannel) and channel.guild.id == guild.id


async def send_log_message(log_channel: GuildChannel, embed_func, **args):
    """
    Log message handler
    """
    if not log_channel or not isinstance(log_channel, Messageable):
        return
    embed = await embed_func(**args) if iscoroutinefunction(embed_func) else embed_func(**args)
    if not embed:
        return
    await log_channel.send(embed=embed)


async def is_ignored(config: Config, member: Member, guild: Guild, channel: GuildChannel=None) -> bool:
    return (await config.guild(guild).ignored()
            or member and (member.bot or await config.member(member).ignored())
            or (await config.channel(channel).ignored() if channel and isinstance(channel, TextChannel) else False)
            or False)
