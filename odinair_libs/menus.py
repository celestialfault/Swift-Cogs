from asyncio import TimeoutError

from enum import Enum
from typing import Union, Any, Dict, Sequence, Callable, Tuple

import discord
from redbot.core import RedContext

__all__ = ["PostMenuAction", "ReactMenu", "MenuResult", "paginate", "confirm", "cmd_help"]


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

    def __repr__(self):
        return (
            f"<ReactMenu content={self.content!r} embed={self.embed!r} message={self.message!r} "
            f"default={self.default!r} action_count={len(self.actions)} post_action={self.post_action} "
            f"member={self.member!r}>"
        )

    async def _add_reactions(self):
        """Internal task to add reactions to sent messages"""
        try:
            for emoji in self.emojis:
                _reaction = discord.utils.get(self.message.reactions, emoji=emoji)
                if _reaction is None or _reaction.me is False:
                    await self.message.add_reaction(emoji)
        except (discord.HTTPException, AttributeError) as e:
            # check if the exception is a bad request
            if isinstance(e, discord.HTTPException) and e.status == 400:
                raise
            # ... silently swallow it otherwise

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
        ret = (msg.id == self.message.id and user.id == self.member.id
               and (str(reaction.emoji) in self.emojis or reaction.emoji in self.emojis))
        return ret

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
        self.message = getattr(menu, "message", None)

    def __str__(self):
        return str(self.action)

    def __eq__(self, other):
        return isinstance(other, MenuResult) and self.action == other.action

    def __repr__(self):
        return f"<MenuResult action={self.action!r} timed_out={self.timed_out} menu={self.menu!r}>"

    async def reinvoke(self):
        """Reinvoke the reaction menu"""
        return await self.menu.prompt()


async def paginate(ctx: RedContext, pages: Sequence[Any], page: int = 0,
                   title: str = discord.Embed.Empty, colour: discord.Colour = discord.Embed.Empty,
                   actions: Dict[Any, Union[str, discord.Emoji]] = None,
                   page_converter: Callable[[Any], Union[str, discord.Embed]] = None,
                   **kwargs) -> Tuple[MenuResult, Any]:
    """Pagination helper

    Parameters
    -----------
    ctx: RedContext
        The Red context object
    pages: Sequence[Any]
        A sequence of page items. If these are neither string nor Embed objects,
        it's expected that a ``page_converter`` function is given to convert them into string or Embed objects.
    page: int
        The page shown upon creating the pagination menu
    title: str
        The embed title
    colour: discord.Colour
        The embed colour
    actions: Dict[Any, Union[str, discord.Emoji]]
        A list of actions. If any of these are selected, then the function returns with a Tuple of
        the MenuResult and the current page.
    page_converter: Callable[[Any], str]
        An optional page converter function. This is expected to be given if the items in ``pages`` are not
        string or embed objects.

    Returns
    --------
    Tuple[MenuResult, Any]
        The MenuResult returned from ReactMenu and the current page

    Raises
    -------
    ValueError
        Raised if no pages are given
    TypeError
        Raised if ``page_converter`` returns a value that isn't `str` or `discord.Embed`, or if any item
        in ``pages`` is neither of the two and ``page_converter`` is not given
    """
    if len(pages) == 0:
        raise ValueError("No pages were given")
    if actions is None:
        actions = {}
    actions = {
        "__paginate_backward": "\N{LEFTWARDS BLACK ARROW}",
        **{x: actions[x] for x in actions},
        "__paginate_forward": "\N{BLACK RIGHTWARDS ARROW}"
    }

    def build_embed():
        description = pages[page]
        if page_converter:
            description = page_converter(description)
        if isinstance(description, str):
            embed = discord.Embed(title=title, description=description, colour=colour)
            embed.set_footer(text="Page {}/{}".format(page + 1, len(pages)))
        elif isinstance(description, discord.Embed):
            embed = description
        else:
            raise TypeError(f"Description for page index {page} is neither a str nor Embed type")
        return embed

    menu = ReactMenu(ctx=ctx, actions=actions, embed=build_embed(), post_action=PostMenuAction.REMOVE_REACTION,
                     **kwargs)
    result = None
    while True:
        if hasattr(result, "message"):
            await result.message.edit(embed=build_embed())
        result = await menu.prompt()
        if result == "__paginate_backward":
            if page == 0:
                continue
            page -= 1
            continue
        elif result == "__paginate_forward":
            if page >= len(pages) - 1:
                continue
            page += 1
            continue
        elif result.timed_out:
            try:
                await result.message.clear_reactions()
            except (discord.HTTPException, AttributeError):
                pass
        return result, pages[page]


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
        f"{message}\n\n"
        f"**Click \N{WHITE HEAVY CHECK MARK} to confirm or \N{REGIONAL INDICATOR SYMBOL LETTER X} to cancel**"
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
    # This probably isn't the cleanest solution, but it works well enough,
    # so this is mostly what I'd consider "good enough"
    if not ctx.invoked_subcommand or ctx.invoked_subcommand.name == cmd:
        await ctx.send_help()
