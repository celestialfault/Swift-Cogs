import asyncio
from typing import Union

import discord
from redbot.core import RedContext
from redbot.core.bot import Red


async def confirm(bot: Red, ctx: RedContext, message: str, timeout: Union[float, int] = 30.0,
                  colour: discord.Colour = discord.Colour.blurple()):
    """Prompt a user for confirmation"""
    actions = {"\N{WHITE HEAVY CHECK MARK}": "confirm", "\N{REGIONAL INDICATOR SYMBOL LETTER X}": "cancel"}
    message = ("{}\n\n"
               "**Click \N{WHITE HEAVY CHECK MARK} to confirm or "
               "\N{REGIONAL INDICATOR SYMBOL LETTER X} to cancel**"
               "".format(message))
    return await react_menu(bot, ctx, message, actions, default="\N{REGIONAL INDICATOR SYMBOL LETTER X}",
                            timeout=timeout, colour=colour) == "confirm"


async def react_menu(bot: Red, ctx: RedContext, message: str, actions: dict, member: discord.Member = None,
                     default: str = None, colour: discord.Colour = discord.Colour.blurple(),
                     timeout: Union[float, int] = 30.0, delete_msg: bool = True):
    if len(actions.keys()) > 15:
        raise RuntimeError("You can only have at most 15 different actions")
    member = member or ctx.author
    embed = discord.Embed(description=message, colour=colour)
    react_msg = await ctx.send(embed=embed)

    for emoji in actions.keys():
        await react_msg.add_reaction(emoji)

    def check(_react, _user):
        msg = _react.message
        return msg.id == react_msg.id and _user.id == member.id and str(_react.emoji) in actions.keys()

    _ret_val = None

    try:
        reaction, emoji = await bot.wait_for("reaction_add", check=check, timeout=timeout)
    except asyncio.TimeoutError:
        _ret_val = actions.get(default, None)
    else:
        _ret_val = actions.get(str(reaction.emoji), actions.get(default, None))
    finally:
        if delete_msg:
            await react_msg.delete()
        else:
            if getattr(ctx, "guild", None) and ctx.channel.permissions_for(ctx.guild.me).manage_messages:
                await react_msg.clear_reactions()
        return _ret_val


async def cmd_help(ctx: RedContext, cmd: str) -> None:
    """Sends sub-command help"""
    if not ctx.invoked_subcommand or ctx.invoked_subcommand.name == cmd:
        await ctx.send_help()
