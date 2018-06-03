"""Interactive reaction menus

Designed for easy portability with other discord.py bots.
"""

import asyncio
from enum import IntEnum
from types import GeneratorType
from typing import Any, Awaitable, Callable, Coroutine, Dict, Optional, Sequence, Tuple, Union

import discord
from discord.ext import commands

__author__ = "odinair <odinair@odinair.xyz>"
__all__ = ["PostAction", "Result", "Menu", "PaginatedMenu", "Page"]


def try_get(cls, name: str, kwargs: dict = None):
    if kwargs is None:
        kwargs = {}
    v = getattr(cls, name, kwargs.get(name, None))
    if v is not None:
        return v
    raise TypeError(f"required argument {name} is missing")


class PostAction(IntEnum):
    """Determines the action a Menu takes after having received (or not received) user input"""
    NO_ACTION = 0
    REMOVE_REACTION = 1
    CLEAR_REACTIONS = 2
    DELETE_MESSAGE = 3

    def __str__(self):
        return self.name.replace("_", " ").capitalize()


class Result:
    """Result from a Menu object"""

    def __init__(self, item: Any, reaction: Optional[discord.Reaction], menu: "Menu", **kwargs):
        self.item = item
        self.reaction = reaction
        self.menu = menu
        self.extra = kwargs

    def __repr__(self):
        return (
            f"Result(item={self.item!r}, reaction={self.reaction!r}, menu={self.menu!r}, "
            f"timed_out={self.timed_out})"
        )

    def __getattr__(self, item):
        if item in self.extra:
            return self.extra[item]
        raise AttributeError

    def __eq__(self, other):
        return self.item == other

    def __gt__(self, other):
        return self.item > other

    def __lt__(self, other):
        return self.item < other

    @property
    def timed_out(self) -> bool:
        return self.reaction is None

    @property
    def message(self):
        return self.menu.message


###########################
#   Normal Menu


class Menu(Awaitable):

    def __init__(self, actions: Dict[Any, Union[discord.Emoji, str]], **kwargs):
        """Create a new reaction menu

        Parameters
        -----------
        actions: Dict[Any, Union[discord.Emoji, str]]
            The actions users can perform with this

        Keyword Arguments
        -------------------
        ctx: commands.Context
            Optional command context object.
            If this is given, `member`, `channel` and `bot` are optional arguments.
        channel: discord.TextChannel
            The channel to send to. If `ctx` is given, this is optional.
        bot: commands.Bot
            The Discord bot instance. If `ctx` is given, this is optional.
        member: discord.Member
            The member to listen for reactions from. If `ctx` is given, this is optional.
        content: str
            Content string to pass to `channel.send()`. This and/or `embed` are required.
        embed: discord.Embed
            An embed to pass to `channel.send()`. This and/or `content` are required.
        message: discord.Message
            Optional Message object to re-use.
        default: Any
            The default value to return if a prompt times out.
        timeout: float
            How long to wait in seconds before timing out. If this is set to `0`, this is disabled.
            Set to `30.0` by default.
        """

        if "ctx" in kwargs:
            ctx: commands.Context = kwargs["ctx"]
            self.channel = ctx.channel
            self.member = ctx.author
            self.bot = ctx.bot

        self.channel: discord.TextChannel = try_get(self, "channel", kwargs=kwargs)
        self.member: discord.Member = try_get(self, "member", kwargs=kwargs)
        self.bot: commands.Bot = try_get(self, "bot", kwargs=kwargs)

        if not all(isinstance(x, (str, discord.Emoji)) for x in actions.values()):
            raise RuntimeError("not all action values are of type str or discord.Emoji")

        if len(set(actions.values())) != len(list(actions.values())):
            raise RuntimeError("one or more emojis in the given actions is duplicated")
        self.actions = actions

        self.content: Optional[str] = kwargs.get("content", None)
        self.embed: Optional[discord.Embed] = kwargs.get("embed", None)
        self._allow_empty = getattr(self, "_allow_empty", False)
        if not any([self.content, self.embed, self._allow_empty]):
            raise RuntimeError("neither content nor embed kwargs were given")

        self.message: Optional[discord.Message] = kwargs.get("message", None)
        self.default: Any = kwargs.get("default", None)
        self.timeout: float = kwargs.get("timeout", 30.0)
        self._react_task: Optional[asyncio.Task] = None

    def __await__(self):
        return self.prompt().__await__()

    @property
    def keys(self):
        return list(self.actions.keys())

    @property
    def emojis(self):
        return list(self.actions.values())

    @property
    def guild(self) -> discord.Guild:
        return getattr(self.channel, "guild", None)

    @property
    def send(self) -> Callable:
        return self.channel.send

    ############################

    async def prompt(
        self, *, post_action: PostAction = PostAction.REMOVE_REACTION, clear_on_timeout: bool = True
    ) -> Result:
        res = await self.listen_for_reaction()
        if (
            res.timed_out
            and clear_on_timeout
            and post_action not in (PostAction.CLEAR_REACTIONS, PostAction.DELETE_MESSAGE)
        ):
            post_action = PostAction.CLEAR_REACTIONS

        return await self.handle_post(res, post_action)

    async def listen_for_reaction(self) -> Result:
        await self.send_message()
        self._react_task = self.bot.loop.create_task(self.add_reactions())

        try:
            reaction, _ = await self.bot.wait_for(
                "reaction_add", timeout=self.timeout, check=self.reaction_check
            )
        except asyncio.TimeoutError:
            reaction = None
        finally:
            if self._react_task:
                self._react_task.cancel()

        return self.get_result(reaction)

    async def send_message(self):
        if self.message is not None:
            await self.message.edit(content=self.content, embed=self.embed)
            return
        self.message = await self.send(content=self.content, embed=self.embed)

    async def add_reactions(self):
        try:
            for emoji in self.emojis:
                emoji_reaction: Optional[discord.Reaction] = discord.utils.get(
                    self.message.reactions, emoji=emoji
                )
                if emoji_reaction is None or not emoji_reaction.me:
                    await self.message.add_reaction(emoji)
        except (discord.HTTPException, AttributeError):
            pass

    def reaction_check(self, reaction: discord.Reaction, member: discord.Member):
        return all(
            [
                reaction.emoji in self.emojis,
                member == self.member,
                reaction.message.id == self.message.id,
            ]
        )

    def get_result(self, reaction: Optional[discord.Reaction]):
        return Result(
            item=(
                self.keys[self.emojis.index(reaction.emoji)]
                if reaction is not None
                else self.default
            ),
            reaction=reaction,
            menu=self,
        )

    async def handle_post(self, result: Result, post_action: PostAction) -> Result:
        if post_action == PostAction.NO_ACTION:
            return result

        try:
            if self.guild and self.channel.permissions_for(self.guild.me).manage_messages:
                if post_action == PostAction.CLEAR_REACTIONS:
                    await self.message.clear_reactions()
                elif post_action == PostAction.REMOVE_REACTION:
                    await self.message.remove_reaction(result.reaction.emoji, self.member)

            if post_action == PostAction.DELETE_MESSAGE and self.message:
                await self.message.delete()
                self.message = None
        except (AttributeError, discord.HTTPException):
            pass

        return result


############################
#   Paginated Menu


class Page:
    """Page data class for PaginatedMenu"""

    def __init__(self, data: Any, current: int, total: int):
        self.data = data
        self.true_current = current
        self.true_total = total

    @property
    def total(self):
        """Returns a human friendly amount of pages"""
        return self.true_total + 1

    @property
    def current(self):
        """Returns a human friendly page index"""
        return self.true_current + 1


class PaginatedMenu(Menu):
    """Paginated variation of Menu"""

    def __init__(
        self,
        pages: Sequence[Any],
        actions: Optional[Dict[Any, Union[discord.Emoji, str]]] = None,
        converter: Callable[
            [Page], Union[Coroutine, str, discord.Embed, Tuple[str, discord.Embed]]
        ] = None,
        **kwargs,
    ):
        """Create a paginated version of a Menu

        All keyword arguments not specified below are passed to `Menu`, with the exception
        of `content` and `embed`.

        Parameters
        ------------
        pages: Sequence[Any]
            The pages to iterate through
        actions: Optional[Dict[Any, Union[discord.Emoji, str]]]
            An optional list of actions a user can perform. The given actions will always be
            surrounded by internal paginate actions.
        converter: Callable[[Page], Union[str, discord.Embed, Tuple[str, discord.Embed]]]
            An optional converter function, that must have a return type of `str`,
            `discord.Embed`, or `Tuple[str, discord.Embed]`.

        Keyword Arguments
        -------------------
        wrap_around: bool
            If this is True, users attempting to go to the previous page at the first page, or
            forwards at the last page, will result in wrapping around to the last or first
            page respectively.

        """
        if isinstance(pages, GeneratorType):
            pages = list(pages)

        if not pages:
            raise RuntimeError("no pages were given to iterate through")

        self.pages = pages
        self._allow_empty = True

        super().__init__(
            actions={
                "__paginate_back": "\N{LEFTWARDS BLACK ARROW}",
                **(actions or {}),
                "__paginate_fwd": "\N{BLACK RIGHTWARDS ARROW}",
            },
            content=None,
            embed=None,
            **kwargs,
        )

        self.converter = converter or (
            lambda x: (
                discord.Embed(description=str(x.data)).set_footer(
                    text=f"Page {x.current} out of {x.total}"
                )
            )
        )
        self.current_page: int = kwargs.get("page", 0)
        self.wrap_around: bool = kwargs.get("wrap_around", False)

    @property
    def max_pages(self):
        return len(self.pages) - 1

    ############################

    async def prompt(
        self, *, post_action: PostAction = PostAction.CLEAR_REACTIONS, clear_on_timeout: bool = True
    ) -> Result:
        """Start a paginated menu.

        The Result returned contains an extra `page` data value, containing the page that was active
        when the menu exited.
        """
        while True:
            data = await discord.utils.maybe_coroutine(
                self.converter,
                Page(
                    data=self.pages[self.current_page],
                    current=self.current_page,
                    total=self.max_pages,
                ),
            )

            if isinstance(data, tuple):
                self.content = data[0]
                self.embed = data[1]
            elif isinstance(data, discord.Embed):
                self.embed = data
            elif isinstance(data, str):
                self.content = data
            else:
                raise RuntimeError(
                    "converter did not return any of types tuple(str, discord.Embed), "
                    "discord.Embed, or str"
                )

            result = await super().prompt(
                post_action=PostAction.REMOVE_REACTION, clear_on_timeout=clear_on_timeout
            )
            if result.timed_out:
                return result

            if result == "__paginate_back":
                if self.current_page == 0:
                    if self.wrap_around is True:
                        self.current_page = self.max_pages
                    continue
                self.current_page -= 1
            elif result == "__paginate_fwd":
                if self.current_page == self.max_pages:
                    if self.wrap_around is True:
                        self.current_page = 0
                    continue
                self.current_page += 1

            else:
                return await self.handle_post(result, post_action)

    def get_result(self, reaction: Optional[discord.Reaction]):
        result = super().get_result(reaction)
        result.extra["page"] = self.pages[self.current_page]
        return result
