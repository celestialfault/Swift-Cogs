from asyncio import TimeoutError

from collections import namedtuple
from enum import Enum
from typing import Union, Any, Dict

import discord
from redbot.core import RedContext


class PostMenuAction(Enum):
    """The action to take after a menu action or timeout"""
    DELETE = "delete"
    CLEAR_REACTIONS = "clear_react"
    REMOVE_REACTION = "remove_react"
    NONE = "none"


MenuResult = namedtuple("MenuResult", "action message timed_out")


async def confirm(ctx: RedContext, message: str, timeout: float = 30.0,
                  colour: discord.Colour = discord.Colour.blurple(), default: bool = False, **kwargs) -> bool:
    """Prompt a user for confirmation on an action

    Parameters
    -----------

        ctx: RedContext

            The Red context object

        message: str

            The message to display on the confirmation prompt

        timeout: float

            How long to wait in seconds before timing out with the default value

            This can be set to `None` to disable the timeout, however it is not recommended.

            Default value: 30.0

        colour: discord.Colour

            The colour to use for the message embed

            Default value: `discord.Colour.blurple()`

        default: bool

            The default return value if the prompt times out

            Default value: `False`

    Returns
    --------

        bool

            A boolean value indicating if the user confirmed or declined the action, or the value of `default`
            if the timeout was reached
    """
    message = (
        "{}\n\n"
        "**Click \N{WHITE HEAVY CHECK MARK} to confirm or \N{REGIONAL INDICATOR SYMBOL LETTER X} to cancel**"
        "".format(message)
    )
    actions = {True: "\N{WHITE HEAVY CHECK MARK}", False: "\N{REGIONAL INDICATOR SYMBOL LETTER X}"}
    return (await react_menu(ctx, actions, embed=discord.Embed(description=message, colour=colour),
                             default=default, timeout=timeout, post_action=PostMenuAction.DELETE,
                             post_action_check=None, **kwargs)).action


async def react_menu(ctx: RedContext, actions: Dict[Any, Union[discord.Emoji, discord.Reaction, str]],
                     **kwargs) -> MenuResult:
    """Create a reaction menu

    Parameters
    -----------

        ctx: RedContext

            The Red context object

        actions: Dict[Any, Union[discord.Emoji, discord.Reaction, str]]

            A dict of actions, similar to {action: emoji, ...}
            There can only be up to 15 different actions

    Keyword args
    -------------

        default: Any

            The default action.

            Default value: `None`

        content: str

            The message content when sending a message if `message` is not specified

            If `message` is given, this value is ignored

            Default value: `None`

        embed: discord.Embed

            A message embed to use when sending a message if `message` is not specified

            If `message` is given, this value is ignored

            Default value: `None`

        message: discord.Message

            A message to re-use. This is best used with the remove reaction action if this is a message
            being re-used from prior react menu calls.

            If this is None and neither `embed` nor `content` is given, a RuntimeError is raised.
            Otherwise, if this is given, `embed` and `content` are ignored.

            Default value: `None`

        member: discord.Member

            The member to listen to reactions from.

            This is set to the value of `ctx.author` if `None` is given.

            Default value: `None`

        timeout: float

            How long to wait for a reaction before timing out.

            Default value: `30.0`

        post_action: PostMenuAction

            The action to take when a user chooses a reaction.
            If the menu times out, this will default to clearing reactions if this is not `PostMenuAction.DELETE`

            This setting is treated as if it was set to `PostMenuAction.CLEAR_REACTIONS`
            if the menu times out and this is not set to `PostMenuAction.DELETE`

            Default value: `PostMenuAction.REMOVE_REACTION`

        post_action_check: Callable[[Any], bool]

            An optional Callable that should return a bool value. If it returns False, `post_action` will be
            treated as if it was set to `PostMenuAction.NONE` when the menu was created

            This setting is ignored if the menu times out

            Default value: `None`

    Returns
    --------

        MenuResult

            A special object containing the action taken, the message sent (if applicable),
            and a bool indicating if the menu timed out.

    Raises
    -------

        discord.Forbidden

            If the bot is not allowed to send messages in the context channel

        discord.HTTPException

            A generic HTTP exception

        ValueError

            Raised if more than 15 different actions are given

        RuntimeError

            Raised if none of either message, embed or content attributes are given
    """
    default = kwargs.get("default", None)
    content = kwargs.get("content", None)
    embed = kwargs.get("embed", None)
    message = kwargs.get("message", None)
    member = kwargs.get("member", ctx.author)
    timeout = kwargs.get("timeout", 30.0)
    post_action = kwargs.get("post_action", PostMenuAction.REMOVE_REACTION)
    post_action_check = kwargs.get("post_action_check", None)

    if len(actions.keys()) > 15:
        raise ValueError("You can only have at most up to 15 different actions")
    if not any([message, embed, content]):
        raise RuntimeError("Expected any of either message, embed, or content attributes, received none")

    member = member or ctx.author
    bot = ctx.bot
    emojis = [actions[x] for x in actions]
    actions = [x for x in actions]

    if not message:
        message = await ctx.send(content=content, embed=embed)

    for emoji in emojis:
        _reaction = discord.utils.get(message.reactions, emoji=emoji)
        if _reaction is None or _reaction.me is False:
            await message.add_reaction(emoji)

    def check(react_, user_):
        msg = react_.message
        return msg.id == message.id and user_.id == member.id and str(react_.emoji) in emojis

    reaction = namedtuple("Reaction", "emoji")(emoji=None)
    ret_val = default
    timed_out = False
    try:
        reaction, _ = await bot.wait_for("reaction_add", check=check, timeout=timeout)
    except TimeoutError:
        timed_out = True
    else:
        if reaction.emoji in emojis:
            ret_val = actions[emojis.index(reaction.emoji)]
    finally:
        if post_action_check is not None and timed_out is not True and post_action_check(ret_val) is False:
            post_action = PostMenuAction.NONE
        if post_action == PostMenuAction.DELETE:
            await message.delete()
        elif getattr(ctx, "guild", None) and ctx.channel.permissions_for(ctx.guild.me).manage_messages:
            if post_action == PostMenuAction.CLEAR_REACTIONS or timed_out:
                await message.clear_reactions()
            elif post_action == PostMenuAction.REMOVE_REACTION:
                await message.remove_reaction(reaction.emoji, member)
        message = message if post_action != PostMenuAction.DELETE else None
        return MenuResult(ret_val, message, timed_out)


async def cmd_help(ctx: RedContext, cmd: str) -> None:
    """Sends sub-command help"""
    if not ctx.invoked_subcommand or ctx.invoked_subcommand.name == cmd:
        await ctx.send_help()
