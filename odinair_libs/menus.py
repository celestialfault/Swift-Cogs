from asyncio import TimeoutError

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


class ReactMenu:
    def __init__(self, ctx: RedContext, actions: Dict[Any, Union[discord.Emoji, discord.Reaction, str]],
                 **kwargs):
        """Create a new reaction menu.

        Parameters
        -----------
        ctx: RedContext
            The Red context object
        actions: Dict[Any, Union[discord.Emoji, str]]
            A dict of actions, similar to {action: emoji, ...}

            There can only be up to 15 different actions

        Keyword args
        -------------
        default: Any
            The default action.

            Default value: ``None``
        content: str
            The message content when sending a message if ``message`` is not specified.
            If ``message`` is given, this value is ignored

            Default value: ``None``
        embed: discord.Embed
            A message embed to use when sending a message if ``message`` is not specified.
            If ``message`` is given, this value is ignored

            Default value: ``None``
        message: discord.Message
            A message to re-use. This is best used with the remove reaction action if this is a message
            being re-used from prior react menu calls.

            If this is None and neither ``embed`` nor ``content`` is given, a RuntimeError is raised.
            Otherwise, if this is given, ``embed`` and ``content`` are ignored.

            Default value: ``None``
        member: discord.Member
            The member to listen to reactions from.

            Default value: ``ctx.author``
        timeout: float
            How long to wait for a reaction before timing out.

            Default value: ``30.0``
        post_action: PostMenuAction
            The action to take when a user chooses a reaction.
            If the menu times out, this will default to clearing reactions if this is not ``PostMenuAction.DELETE``

            This setting is treated as if it was set to ``PostMenuAction.CLEAR_REACTIONS``
            if the menu times out and this is not set to ``PostMenuAction.DELETE``

            Default value: ``PostMenuAction.REMOVE_REACTION``
        post_action_check: Callable[[Any], bool]
            An optional Callable that should return a bool value. If it returns False, ``post_action`` will be
            treated as if it was set to ``PostMenuAction.NONE`` when the menu was created.
            If the menu times out, this value is ignored.

            Default value: ``None``

        Raises
        -------
        ValueError
            Raised if more than 15 different actions are given
        RuntimeError
            Raised if none of either message, embed or content attributes are given
        discord.Forbidden
            Raised if the bot is not allowed to add reactions to messages in the context channel
        """
        if ctx.guild is not None and not ctx.channel.permissions_for(ctx.guild.me).add_reactions:
            raise discord.Forbidden
        if len(actions.keys()) > 15:
            raise ValueError("You can only have at most up to 15 different actions")

        self.ctx = ctx
        self.bot = ctx.bot

        self.content = kwargs.get("content", None)
        self.embed = kwargs.get("embed", None)
        self.message = kwargs.get("message", None)
        if not any([self.message, self.embed, self.content]):
            raise RuntimeError("Expected any of either message, embed, or content attributes, received none")

        self.default = kwargs.get("default", None)
        self.timeout = kwargs.get("timeout", 30.0)
        self.actions = [x for x in actions]
        self.emojis = [actions[x] for x in actions]
        self.post_action = kwargs.get("post_action", PostMenuAction.REMOVE_REACTION)
        self.post_action_check = kwargs.get("post_action_check", None)
        self.member = kwargs.get("member", ctx.author)
        self._reactions_task = None

    async def _add_reactions(self):
        """Internal task to add reactions to sent messages"""
        try:
            for emoji in self.emojis:
                _reaction = discord.utils.get(self.message.reactions, emoji=emoji)
                if _reaction is None or _reaction.me is False:
                    await self.message.add_reaction(emoji)
        except (discord.NotFound, AttributeError):
            return

    async def _handle_post_action(self, timed_out: bool, reaction: discord.Reaction = None, result: Any = None):
        """Internal helper function to handle cleanup"""
        action = self.post_action
        if self._reactions_task is not None:
            self._reactions_task.cancel()
        if not timed_out and self.post_action_check and self.post_action_check(result) is False:
            action = PostMenuAction.NONE

        try:
            if action == PostMenuAction.DELETE:
                await self.message.delete()
                self.message = None
            elif action == PostMenuAction.CLEAR_REACTIONS or timed_out:
                await self.message.clear_reactions()
            elif reaction and action == PostMenuAction.REMOVE_REACTION:
                await self.message.remove_reaction(reaction.emoji, self.member)
        except discord.HTTPException:
            pass

    def _reaction_check(self, reaction: discord.Reaction, user: discord.User):
        """Check for discord.py's wait_for function"""
        msg = reaction.message
        return msg.id == self.message.id and user.id == self.member.id \
               and (str(reaction.emoji) in self.emojis or reaction.emoji in self.emojis)

    async def prompt(self):
        """Prompt for a choice

        Returns
        --------
        MenuResult
            The result from the react menu call. This can be re-invoked with ``MenuResult.reinvoke``
        """
        if not self.message:
            self.message = await self.ctx.send(content=self.content, embed=self.embed)
        self._reactions_task = self.bot.loop.create_task(self._add_reactions())

        ret_val = self.default
        timed_out = False
        try:
            reaction, _ = await self.bot.wait_for("reaction_add", check=self._reaction_check, timeout=self.timeout)
        except TimeoutError:
            timed_out = True
            await self._handle_post_action(True, reaction=None, result=ret_val)
        else:
            if reaction.emoji in self.emojis:
                ret_val = self.actions[self.emojis.index(reaction.emoji)]
            await self._handle_post_action(False, reaction=reaction, result=ret_val)
        finally:
            return MenuResult(action=ret_val, timed_out=timed_out, menu=self)


class MenuResult:
    def __init__(self, action: Any, timed_out: bool, menu: ReactMenu):
        self.action = action
        self.timed_out = timed_out
        self.menu = menu
        self.message = menu.message

    async def reinvoke(self):
        """Reinvoke the reaction menu"""
        return await self.menu.prompt()


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
        How long to wait in seconds before timing out with the default value.
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
    return (await ReactMenu(ctx, actions, embed=discord.Embed(description=message, colour=colour),
                            default=default, timeout=timeout, post_action=PostMenuAction.DELETE,
                            post_action_check=None, **kwargs).prompt()).action


@discord.utils.deprecated(instead="ReactMenu")
async def react_menu(ctx: RedContext, actions: Dict[Any, Union[discord.Emoji, discord.Reaction, str]],
                     **kwargs) -> MenuResult:
    """This function is deprecated and will be removed in the future; please use the ReactMenu class instead"""
    return await ReactMenu(ctx, actions, **kwargs).prompt()


async def cmd_help(ctx: RedContext, cmd: str) -> None:
    """Sends sub-command help"""
    if not ctx.invoked_subcommand or ctx.invoked_subcommand.name == cmd:
        await ctx.send_help()
