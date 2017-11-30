from typing import Optional
from datetime import datetime

from discord import (
    Embed,
    Colour,
    Member,
    TextChannel,
    Message,
    CategoryChannel,
    VoiceState,
    Guild,
    Role
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
    embed = Embed(description=f"Channel {channel.mention} created", colour=Colour.green())
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
        embed.add_field(name="Channel name", value=f"Changed from **{before.name}** to **{after.name}**")
    if isinstance(before, TextChannel) and isinstance(after, TextChannel):
        if before.topic != after.topic:
            before_topic = before.topic or "*No channel topic*"
            after_topic = after.topic or "*No channel topic*"
            embed.add_field(name="Topic changed", value=f"**❯** From:\n{before_topic}\n\n**❯** To:\n{after_topic}",
                            inline=False)
    if before.category != after.category:
        before_name = before.category.name if before.category else "*Uncategorized*"
        after_name = after.category.name if after.category else "*Uncategorized*"
        embed.add_field(name="Category changed",
                        value=f"**❯** From:\n{before_name}\n\n**❯** To:\n{after_name}",
                        inline=False)
    elif before.position != after.position:
        embed.add_field(name="Position changed",
                        value=f"From {before.position} to {after.position}",
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
    if before.name != after.name:
        embed.add_field(name="Username updated", value=f"**❯** From:\n{before.name}\n**❯** After:\n{after.name}",
                        inline=False)
    # Nickname
    if before.nick != after.nick:
        before_nick = escape(before.nick, mass_mentions=True, formatting=True) if before.nick \
            else "*No previous nickname*"
        after_nick = escape(after.nick, mass_mentions=True, formatting=True) if after.nick \
            else "*No nickname*"
        embed.add_field(name="Nickname updated", value=f"**❯** From:\n{before_nick}\n\n**❯** To:\n{after_nick}",
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
#      Guild       #
####################


verification_names = [
    "None",
    "Low",
    "Medium",
    "(╯°□°）╯︵ ┻━┻",
    "┻━┻ ﾐヽ(ಠ益ಠ)ノ彡┻━┻"
]


contentfilter_names = [
    "No filter",
    "Members with no roles",
    "All members"
]


async def embed_guild_update(before: Guild, after: Guild) -> Optional[Embed]:
    embed = Embed(colour=Colour.blue())
    embed.set_author(name="Guild updated", icon_url=after.icon_url)
    embed.set_footer(text="Guild ID: {}".format(after.id))
    if before.name != after.name:
        embed.add_field(name="Name changed",
                        value=f"**❯** From:\n**{before.name}**\n**❯** To:\n**{after.name}**",
                        inline=False)
    if before.verification_level != after.verification_level:
        embed.add_field(name="Verification level changed",
                        value=f"**❯** From **{verification_names[before.verification_level]}**\n"
                              f"**❯** To **{verification_names[after.verification_level]}**",
                        inline=False)
    if before.explicit_content_filter != after.explicit_content_filter:
        embed.add_field(name="Content filter changed",
                        value=f"**❯** From **{contentfilter_names[before.explicit_content_filter]}**\n"
                              f"**❯** To **{contentfilter_names[after.explicit_content_filter]}**",
                        inline=False)
    if before.region != after.region:
        embed.add_field(name="Region changed",
                        value=f"**❯** From **{before.region}**\n**❯** To **{after.region}**",
                        inline=False)
    if before.owner.id != after.owner.id:
        embed.add_field(name="Owner changed",
                        value=f"**❯** From **{before.owner.mention}**\n**❯** To **{after.owner.mention}**",
                        inline=False)
    if before.afk_channel != after.afk_channel:
        before_name = before.afk_channel.name if before.afk_channel else "*No AFK channel*"
        after_name = after.afk_channel.name if after.afk_channel else "*No AFK channel*"
        embed.add_field(name="AFK channel changed",
                        value=f"**❯** From **{before_name}**\n**❯** To **{after_name}**",
                        inline=False)
    if before.afk_timeout != after.afk_timeout:
        embed.add_field(name="AFK timeout changed",
                        value=f"**❯** From **{before.afk_timeout//60} minutes**\n"
                              f"**❯** To **{after.afk_timeout//60} minutes**",
                        inline=False)
    if len(embed.fields) == 0:
        return None
    return embed


####################
#      Roles       #
####################


async def embed_role_create(role: Role) -> Embed:
    embed = Embed(colour=Colour.green())
    embed.set_author(name="Role created", icon_url=role.guild.icon_url)
    embed.description = "Role {} created".format(role.mention)
    return embed


async def embed_role_delete(role: Role) -> Embed:
    embed = Embed(colour=Colour.red())
    embed.set_author(name="Role deleted", icon_url=role.guild.icon_url)
    embed.description = "Role {} deleted".format(role.name)
    return embed


async def embed_role_update(before: Role, after: Role) -> Optional[Embed]:
    embed = Embed(colour=Colour.blue())
    embed.set_author(name="Role updated", icon_url=after.guild.icon_url)
    embed.description = "Role {} updated".format(after.mention)
    embed.set_footer(text="Role ID: {}".format(after.id))
    if before.name != after.name:
        embed.add_field(name="Name changed",
                        value=f"**❯** From:\n**{before.name}**\n**❯** To:\n**{after.name}**",
                        inline=False)
    if before.colour != after.colour:
        before_colour = str(before.colour) if before.colour != Colour.default() else "*No colour*"
        after_colour = str(after.colour) if after.colour != Colour.default() else "*No colour*"
        embed.add_field(name="Colour changed",
                        value=f"**❯** From **{before_colour}**\n**❯** To **{after_colour}**",
                        inline=False)
    if before.position != after.position:
        embed.add_field(name="Position changed",
                        value=f"**❯** From **{before.position}**\n**❯** To **{after.position}**",
                        inline=False)
    if before.hoist != after.hoist:
        embed.add_field(name="Hoist status changed",
                        value="Hoisted" if after.hoist else "Unhoisted",
                        inline=False)
    if before.mentionable != after.mentionable:
        embed.add_field(name="Mention status changed",
                        value="Mentionable" if after.mentionable else "Unmentionable",
                        inline=False)
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
    embed.add_field(name="Author", value=f"{member.mention}\n(User ID: {member.id})")
    embed.add_field(name="Channel", value=after.channel.mention)
    embed.add_field(name="Message Timestamp",
                    value="{}\n"
                          "Edited after {}".format(before.created_at.strftime("%c"),
                                                   await td_format(after.edited_at - after.created_at)),
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
    embed.add_field(name="Author", value="{}\n(User ID: {})".format(member.mention, member.id))
    embed.add_field(name="Channel", value=message.channel.mention)
    embed.add_field(name="Message Timestamp",
                    value="{}\n"
                          "Deleted after {}".format(message.created_at.strftime("%c"),
                                                    await td_format(datetime.utcnow() - message.created_at)),
                    inline=False)
    embed.add_field(name="Content", value=message.content, inline=False)
    if message.attachments and len(message.attachments) > 0:
        embed.add_field(name="Attachments", value="\n".join([x.url for x in message.attachments]), inline=False)
    return embed


####################
#       Voice      #
####################


async def embed_voice(member: Member, before: VoiceState, after: VoiceState, config: Group) -> Optional[Embed]:
    if before.afk or after.afk:  # don't log state changes if the user either already is, coming out of, or entering afk
        return None
    embed = Embed(colour=Colour.dark_grey(), description="Member {}".format(member.mention))
    embed.set_footer(text="User ID: {}".format(member.id))
    embed.set_author(name="Voice state updated", icon_url=member.avatar_url)
    # Voice channel
    if await config.join_part():
        if (before.channel and after.channel) and (before.channel.id != after.channel.id):
            embed.add_field(name="Switched voice channel",
                            value=f"Switched from {before.channel.mention} to {after.channel.mention}")
        elif before.channel and not after.channel:
            embed.add_field(name="Left voice channel", value=f"Left {before.channel.mention}")
        elif not before.channel and after.channel:
            embed.add_field(name="Joined voice channel", value=f"Joined {after.channel.mention}")
    # Muted status
    if await config.mute_unmute():
        if before.mute or after.mute:
            if before.mute and not after.mute:
                embed.add_field(name="Mute status", value="😮🛡 Server unmuted", inline=False)
            elif not before.mute and after.mute:
                embed.add_field(name="Mute status", value="😶🛡 Server muted ", inline=False)
        elif before.self_mute != after.self_mute:
            if before.self_mute and not after.self_mute:
                embed.add_field(name="Mute status", value="😮 Self unmuted", inline=False)
            elif not before.self_mute and after.self_mute:
                embed.add_field(name="Mute status", value="😶 Self muted", inline=False)
    # Deafened status
    if await config.deafen_undeafen():
        if before.deaf or after.deaf:
            if before.deaf and not after.deaf:
                embed.add_field(name="Deafened status", value="🐵🛡 Server undeafened", inline=False)
            elif not before.deaf and after.deaf:
                embed.add_field(name="Deafened status", value="🙉🛡 Server deafened", inline=False)
        elif before.self_deaf != after.self_deaf:
            if before.self_deaf and not after.self_deaf:
                embed.add_field(name="Deafened status", value="🐵 Self undeafened", inline=False)
            elif not before.self_deaf and after.self_deaf:
                embed.add_field(name="Deafened status", value="🙉 Self deafened", inline=False)
    if len(embed.fields) == 0:
        return None
    return embed


###################
#     Globals     #
###################

async def embed_guild_join(guild: Guild) -> Embed:
    bots = len([x for x in guild.members if x.bot])
    users = len([x for x in guild.members if not x.bot])
    bot_percentage = f"{float(bots) / float(guild.member_count):.0%}"
    embed = Embed(colour=Colour.green())
    embed.description = f"Joined guild **{guild.name}**"
    embed.set_author(name="Guild joined", icon_url=guild.icon_url)
    embed.set_footer(text=f"Guild ID: {guild.id}")
    embed.add_field(name="Total non-bot users", value=str(users))
    embed.add_field(name="Total bots", value=f"{bots} ({bot_percentage})")
    return embed


async def embed_guild_leave(guild: Guild) -> Embed:
    embed = Embed(colour=Colour.red())
    embed.description = f"Left guild **{guild.name}**"
    embed.set_author(name="Guild left", icon_url=guild.icon_url)
    embed.set_footer(text=f"Guild ID: {guild.id}")
    return embed
