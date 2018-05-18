"""Legacy interactive menus"""
import warnings
from asyncio import TimeoutError

from enum import Enum
from typing import Union, Any, Dict, Sequence, Tuple, Awaitable
from types import GeneratorType

import discord

from redbot.core.commands import Context

__all__ = ("PostMenuAction", "ReactMenu", "ConfirmMenu", "PaginateMenu", "MenuResult")


class PostMenuAction(Enum):
    DELETE = "delete"
    CLEAR_REACTIONS = "clear_react"
    REMOVE_REACTION = "remove_react"
    NONE = "none"


class MenuResult:

    def __init__(self, action: Any, timed_out: bool, menu: "ReactMenu"):
        self.action = action
        self.timed_out = timed_out
        self.menu = menu

    @property
    def message(self):
        return getattr(self.menu, "message", None)

    def __repr__(self):
        return (
            "<MenuResult action={self.action!r} timed_out={self.timed_out} menu={self.menu!r}>"
        ).format(
            self=self
        )

    def __str__(self):
        return str(self.action)

    def __hash__(self):
        return hash(self.action)

    def __bool__(self):
        return bool(self.action)

    def __lt__(self, other):
        return self.action < other

    def __gt__(self, other):
        return self.action > other

    def __eq__(self, other):
        return self.action == other


class ReactMenu(Awaitable):
    """Deprecated in favour of `Menu`"""

    def __init__(
        self,
        ctx: Context,
        actions: Dict[Any, Union[discord.Emoji, discord.Reaction, str]],
        **kwargs
    ):
        warnings.warn("ReactMenu is deprecated; use `Menu` instead", DeprecationWarning)
        if ctx.guild is not None:
            perms = ctx.channel.permissions_for(ctx.guild.me)  # type: discord.Permissions
            if not all([perms.add_reactions, perms.send_messages]):
                raise RuntimeError("Bot cannot add reactions in the context channel")
        if len(actions.keys()) > 15:
            raise ValueError("You can only have at most up to 15 different actions")

        self.ctx = ctx
        self.bot = ctx.bot

        self.content = kwargs.get("content", None)
        self.embed = kwargs.get("embed", None)
        self.message = kwargs.get("message", None)
        if not any([self.message, self.embed, self.content, getattr(self, "_allow_empty", False)]):
            raise RuntimeError(
                "Expected any of either message, embed, or content attributes, received none"
            )

        self.default = kwargs.get("default", None)
        self.timeout = kwargs.get("timeout", 30.0)
        self.actions = [x for x in actions]
        self.emojis = [actions[x] for x in actions]
        self.post_action = kwargs.get("post_action", PostMenuAction.REMOVE_REACTION)
        self.post_action_check = kwargs.get("post_action_check", None)
        self.member = kwargs.get("member", ctx.author)
        self._reactions_task = None

    def __await__(self):
        return self.prompt().__await__()

    def __repr__(self):
        return (
            "<ReactMenu content={self.content!r} embed={self.embed!r} message={self.message!r} "
            "default={self.default!r} action_count={actions} post_action={self.post_action} "
            "member={self.member!r}>"
        ).format(
            self=self, actions=len(self.actions)
        )

    async def _add_reactions(self):
        """Internal task to add reactions to sent messages"""
        try:
            for emoji in self.emojis:
                _reaction = discord.utils.get(self.message.reactions, emoji=emoji)
                if _reaction is None or _reaction.me is False:
                    await self.message.add_reaction(emoji)
        except (discord.HTTPException, AttributeError) as e:
            # check if the exception is a bad request & re-raise if so
            if isinstance(e, discord.HTTPException) and e.status == 400:
                raise
            # otherwise, silently swallow it

    async def _handle_post_action(
        self, timed_out: bool, reaction: discord.Reaction = None, result: Any = None
    ):
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
        ret = all(
            [
                msg.id == self.message.id,
                user.id == self.member.id,
                str(reaction.emoji) in self.emojis or reaction.emoji in self.emojis,
            ]
        )
        return ret

    async def __aenter__(self):
        return await self.prompt()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def prompt(self) -> MenuResult:
        if not self.message:
            self.message = await self.ctx.send(content=self.content, embed=self.embed)
        self._reactions_task = self.bot.loop.create_task(self._add_reactions())

        ret_val = self.default
        timed_out = False
        reaction = None
        try:
            reaction, _ = await self.bot.wait_for(
                "reaction_add", check=self._reaction_check, timeout=self.timeout
            )
        except TimeoutError:
            timed_out = True
        else:
            if reaction.emoji in self.emojis:
                ret_val = self.actions[self.emojis.index(reaction.emoji)]
        finally:
            await self._handle_post_action(False, reaction=reaction, result=ret_val)
        return MenuResult(action=ret_val, timed_out=timed_out, menu=self)


class ConfirmMenu(ReactMenu):
    """Deprecated in favour of `confirm`"""

    def __init__(self, ctx: Context, default: bool = False, **kwargs):
        warnings.warn("ConfirmMenu is deprecated; use `confirm` instead", DeprecationWarning)
        actions = {True: "\N{WHITE HEAVY CHECK MARK}", False: "\N{CROSS MARK}"}

        if "message" in kwargs:
            kwargs["content"] = kwargs.pop("message")

        # noinspection PyDeprecation
        super().__init__(
            ctx,
            actions,
            default=default,
            post_action=kwargs.pop("post_action", PostMenuAction.DELETE),
            post_action_check=None,
            **kwargs
        )

    async def prompt(self) -> bool:
        return (await super().prompt()).action


class PaginateMenu(ReactMenu):
    """Deprecated in favour of `PaginatedMenu`"""

    def __init__(
        self,
        ctx: Context,
        actions: Dict[Any, Union[discord.Emoji, discord.Reaction, str]],
        pages: Union[Sequence[Any], GeneratorType],
        **kwargs
    ):
        """Create a pagination menu

        Page switching is handled internally and any uses of the paginate buttons are not returned
        to the calling function.

        All keyword arguments not specified below are passed to ReactMenu.

        Unsupported Arguments
        ----------------------

        The following attributes cannot be set:

        - post_action
            This is always `PostMenuAction.CLEAR_REACTIONS`.
        - post_action_check
            This is always `None`.

        Parameters
        -----------
        ctx: Context
            The Red context object
        actions: Dict[Any, Union[discord.Emoji, discord.Reaction, str]]
            The list of actions to allow members to perform.
            A set of two paginate actions are always surrounding the given actions,
            however the paginate actions are handled internally and are never returned.
        pages: Union[Sequence[Any], GeneratorType]
            A sequence of pages. If `converter` is not given, this is expected to contain
            either strings, or objects that can be casted to strings.

        Keyword Arguments
        ------------------

        page: int
            The page index to start on. Defaults to `0`
        converter: Callable[[Any, int, int], Union[str, discord.Embed, Tuple[str, discord.Embed]]]
            A converter to use to convert the items in `pages`. This defaults to a generic Embed
            converter with the item as the description with a plain 'Page {}/{}' footer.

            The call signature is as follows:

            - page_data: `Any`
            - current_page_index: `int`
            - total_pages: `int`

            `current_page_index` is the current index of `pages`,
            whereas `total_pages` is the result of `len(pages)`.

            This can return any of the following types:

            - str
            - discord.Embed
            - tuple(str, discord.Embed)
        wrap_around: bool
            If this is True, paginate actions at the end or beginning trying to go
            forward or backward respectively will wrap around to the end or beginning
            of `pages`.
        """
        warnings.warn("PaginateMenu is deprecated; use `PaginatedMenu` instead", DeprecationWarning)
        actions = {
            "__paginate_backward": "\N{LEFTWARDS BLACK ARROW}",
            **{x: actions[x] for x in actions},
            "__paginate_forward": "\N{BLACK RIGHTWARDS ARROW}",
        }

        if isinstance(pages, GeneratorType):
            pages = list(pages)
        self.pages = pages
        self.page = kwargs.pop("page", 0)
        self.converter = kwargs.pop(
            "converter",
            lambda x, page, pages_: discord.Embed(description=str(x)).set_footer(
                text="Page {}/{}".format(page + 1, pages_)
            ),
        )

        self.wrap_around = kwargs.pop("wrap_around", False)
        self._allow_empty = True

        # noinspection PyDeprecation
        super().__init__(
            ctx,
            actions,
            post_action=PostMenuAction.CLEAR_REACTIONS,
            post_action_check=None,
            **kwargs
        )

    async def prompt(self) -> Tuple[MenuResult, Any]:
        result = None
        while True:
            val = await discord.utils.maybe_coroutine(
                self.converter, self.pages[self.page], self.page, len(self.pages)
            )
            if isinstance(val, tuple):
                self.content = val[0]
                self.embed = val[1]
            elif isinstance(val, str):
                self.content = val
            else:
                self.embed = val

            try:
                await result.message.edit(embed=self.embed)
            except AttributeError:
                pass

            result = await super().prompt()
            if result == "__paginate_backward":
                if self.page == 0:
                    if self.wrap_around:
                        self.page = len(self.pages) - 1
                    continue
                self.page -= 1
                continue
            elif result == "__paginate_forward":
                if self.page >= len(self.pages) - 1:
                    if self.wrap_around:
                        self.page = 0
                    continue
                self.page += 1
                continue
            else:
                if result.timed_out:
                    try:
                        await self.message.clear_reactions()
                    except (discord.HTTPException, AttributeError):
                        pass
                break

        return result, self.pages[self.page]
