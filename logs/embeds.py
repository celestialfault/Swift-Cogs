from typing import Optional
from datetime import datetime

from discord import (
    Embed,
    Colour,
    Member,
    TextChannel,
    Message,
    CategoryChannel,
    VoiceState
)
from discord.abc import GuildChannel
from redbot.core.config import Group
from redbot.core.utils.chat_formatting import escape


# ~~stolen~~ borrowed from StackOverflow
# https://stackoverflow.com/a/13756038
async def td_format(td_object):
    seconds = int(td_object.total_seconds())
    periods = [
        ('year', 60 * 60 * 24 * 365),
        ('month', 60 * 60 * 24 * 30),
        ('day', 60 * 60 * 24),
        ('hour', 60 * 60),
        ('minute', 60),
        ('second', 1)
    ]

    strings = []
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            if period_value == 1:
                strings.append("%s %s" % (period_value, period_name))
            else:
                strings.append("%s %ss" % (period_value, period_name))

    return ", ".join(strings)


####################
#     Channels     #
####################


async def embed_channel_create(channel: GuildChannel) -> Embed:
    """
    Returns a built embed for channel creations
    """
    embed = Embed(description="Channel {} created".format(channel.mention), colour=Colour.green())
    embed.set_author(name="Channel created", icon_url=channel.guild.icon_url)
    return embed


async def embed_channel_delete(channel: GuildChannel) -> Embed:
    """
    Returns a built embed for channel deletions
    """
    channel_type = "Channel" if not isinstance(channel, CategoryChannel) else "Category"
    # noinspection PyUnresolvedReferences
    embed = Embed(description="{} `{}` deleted\n\n"
                              "The channel existed for {}".format(channel_type,
                                                                  channel.name,
                                                                  await td_format(datetime.utcnow()
                                                                                  - channel.created_at)),
                  colour=Colour.red())
    embed.set_author(name="Channel deleted", icon_url=channel.guild.icon_url)
    return embed


async def embed_channel_update(before: GuildChannel, after: GuildChannel) -> Optional[Embed]:
    """
    Returns a built embed for channel updates
    """
    embed = Embed(colour=Colour.blue())
    embed.description = "Channel {} updated".format(before.mention)
    embed.set_author(name="Channel updated", icon_url=before.guild.icon_url)
    # maybe eventually PyCharm will learn that a name field does exist.
    # maybe eventually.
    # noinspection PyUnresolvedReferences
    if before.name != after.name:
        # noinspection PyUnresolvedReferences
        embed.add_field(name="Channel name", value="Changed from **{}** to **{}**".format(before.name, after.name))
    if isinstance(before, TextChannel) and isinstance(after, TextChannel):
        if before.topic != after.topic:
            before_topic = before.topic or "*No channel topic*"
            after_topic = after.topic or "*No channel topic*"
            embed.add_field(name="Topic changed", value="**❯** From:\n{}\n\n**❯** To:\n{}".format(before_topic,
                                                                                                  after_topic),
                            inline=False)
    if before.category != after.category:
        before_name = before.category.name if before.category else "*Uncategorized*"
        after_name = after.category.name if after.category else "*Uncategorized*"
        embed.add_field(name="Category changed",
                        value="**❯** From:\n{}\n\n**❯** To:\n{}".format(before_name, after_name),
                        inline=False)
    elif before.position != after.position:
        embed.add_field(name="Position changed",
                        value="From {} to {}".format(before.position, after.position),
                        inline=False)
    if len(embed.fields) == 0:
        return None
    return embed


####################
#      Members     #
####################


async def embed_member_join(member: Member) -> Embed:
    """
    Returns a built embed for members joining
    """
    embed = Embed(colour=Colour.green())
    embed.set_author(name="Member joined", icon_url=member.avatar_url)
    embed.set_footer(text="User ID: {}".format(member.id))
    embed.description = "**{}**\n\n(account is {} old)".format(str(member),
                                                               await td_format(member.created_at - member.joined_at))
    embed.colour = Colour.green()
    return embed


async def embed_member_leave(member: Member) -> Embed:
    """
    Returns a built embed for members leaving
    """
    embed = Embed(colour=Colour.red())
    embed.set_author(name="Member left", icon_url=member.avatar_url)
    embed.set_footer(text="User ID: {}".format(member.id))
    embed.description = "**{}**\n\n(was a member for {})".format(str(member),
                                                                 await td_format(member.joined_at - datetime.utcnow()))
    embed.colour = Colour.green()
    return embed


async def embed_member_update(before: Member, after: Member) -> Optional[Embed]:
    """
    Returns a built embed for member updates
    """
    # Generic embed data
    embed = Embed(colour=Colour.blue())
    embed.set_author(name="Member updated", icon_url=after.avatar_url)
    embed.description = "Member: {}".format(after.mention)
    embed.set_footer(text="User ID: {}".format(after.id))
    # Username
    if before.discriminator != after.discriminator:
        embed.add_field(name="Discriminator changed", value="**❯** From **{}**\n**❯** To **{}**"
                        .format(before.discriminator, after.discriminator))
    if before.name != after.name:
        embed.add_field(name="Username updated", value="**❯** From:\n```\n{}\n```\n\n**❯** After:\n```\n{}\n```"
                        .format(before.name, after.name),
                        inline=False)
    # Nickname
    if before.nick != after.nick:
        before_nick = escape(before.nick, mass_mentions=True, formatting=True) if before.nick \
            else "*No previous nickname*"
        after_nick = escape(after.nick, mass_mentions=True, formatting=True) if after.nick \
            else "*No nickname*"
        embed.add_field(name="Nickname updated", value="**❯** From:\n{}\n\n**❯** To:\n{}"
                        .format(before_nick, after_nick),
                        inline=False)
    # Roles
    added_roles = []
    for role in after.roles:
        if role in before.roles:
            continue
        added_roles.append(role)
    if len(added_roles) > 0:
        embed.add_field(name="Roles added", value=", ".join([x.name for x in added_roles]), inline=False)
    removed_roles = []
    for role in before.roles:
        if role in after.roles:
            continue
        removed_roles.append(role)
    if len(removed_roles) > 0:
        embed.add_field(name="Roles removed", value=", ".join([x.name for x in removed_roles]), inline=False)
    # Return
    if len(embed.fields) == 0:
        return None
    return embed


####################
#     Messages     #
####################


async def embed_message_edit(before: Message, after: Message) -> Optional[Embed]:
    """
    Returns a built embed for message edits
    """
    if after.author.bot:
        return None
    if not before or not after:
        return None
    member = after.author
    embed = Embed(colour=Colour.blue())
    embed.set_author(name="Message edited", icon_url=member.avatar_url)
    embed.set_footer(text="Message ID: {}".format(after.id))
    embed.add_field(name="Author", value="{}\n(User ID {})".format(member.mention, member.id))
    embed.add_field(name="Channel", value=after.channel.mention)
    embed.add_field(name="Message Timestamp",
                    value="{}\n"
                          "Edited after {}".format(before.created_at.strftime("%c"),
                                                   await td_format(
                                                       after.edited_at - after.created_at)),
                    inline=False)
    embed.add_field(name="Before", value=before.content, inline=False)
    embed.add_field(name="After", value=after.content, inline=False)
    return embed


async def embed_message_delete(message: Message) -> Optional[Embed]:
    """
    Returns a built embed for message deletions
    """
    if message.author.bot:
        return None
    if not message:
        return None
    member = message.author
    embed = Embed(colour=Colour.red())
    embed.set_author(name="Message deleted", icon_url=member.avatar_url)
    embed.set_footer(text="Message ID: {}".format(message.id))
    embed.add_field(name="Author", value="{}\n(User ID {})".format(member.mention, member.id))
    embed.add_field(name="Channel", value=message.channel.mention)
    embed.add_field(name="Message Timestamp",
                    value="{}\n"
                          "Deleted after {}".format(message.created_at.strftime("%c"),
                                                    await td_format(
                                                        datetime.utcnow() - message.created_at)),
                    inline=False)
    embed.add_field(name="Content", value=message.content, inline=False)
    if message.attachments and len(message.attachments) > 0:
        embed.add_field(name="Attachments", value="\n".join([x.url for x in message.attachments]), inline=False)
    return embed


####################
#       Voice      #
####################


async def embed_voice(member: Member, before: VoiceState, after: VoiceState, config: Group) -> Optional[Embed]:
    if before.afk != after.afk:  # don't log afk state changes
        return None
    embed = Embed(colour=Colour.blue(), description="Member {}".format(member.mention))
    embed.set_footer(text="User ID {}".format(member.id))
    embed.set_author(name="Voice state updated", icon_url=member.avatar_url)
    # Voice channel
    if await config.join_part():
        if (before.channel and after.channel) and (before.channel.id != after.channel.id):
            embed.add_field(name="Switched voice channel", value="Switched from {} to {}".format(before.channel.mention,
                                                                                                 after.channel.mention))
        elif before.channel and not after.channel:
            embed.add_field(name="Left voice channel", value="Left {}".format(before.channel.mention))
        elif not before.channel and after.channel:
            embed.add_field(name="Joined voice channel", value="Joined {}".format(after.channel.mention))
    # Muted status
    if await config.mute_unmute():
        if before.mute or after.mute:
            if before.mute and not after.mute:
                embed.add_field(name="Mute status", value="😮 Unmuted **(server mute)**", inline=False)
            elif not before.mute and after.mute:
                embed.add_field(name="Mute status", value="😶 Muted **(server mute)**", inline=False)
        elif before.self_mute != after.self_mute:
            if before.self_mute and not after.self_mute:
                embed.add_field(name="Mute status", value="😮 Unmuted (self mute)", inline=False)
            elif not before.self_mute and after.self_mute:
                embed.add_field(name="Mute status", value="😶 Muted (self mute)", inline=False)
    # Deafened status
    if await config.deafen_undeafen():
        if before.deaf or after.deaf:
            if before.deaf and not after.deaf:
                embed.add_field(name="Deafened status", value="🐵 Undeafened **(server deafen)**", inline=False)
            elif not before.deaf and after.deaf:
                embed.add_field(name="Deafened status", value="🙉 Deafened **(server deafen)**", inline=False)
        elif before.self_deaf != after.self_deaf:
            if before.self_deaf and not after.self_deaf:
                embed.add_field(name="Deafened status", value="🐵 Undeafened (self deafen)", inline=False)
            elif not before.self_deaf and after.self_deaf:
                embed.add_field(name="Deafened status", value="🙉 Deafened (self deafen)", inline=False)
    if len(embed.fields) == 0:
        return None
    return embed
