from asyncio import TimeoutError

from enum import Enum
from typing import Union, Any, Dict, Sequence, Optional

import discord

from redbot.core import RedContext
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import question

__all__ = ("PostMenuAction", "ReactMenu", "ConfirmMenu", "PaginateMenu", "MenuResult", "prompt")


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
        self.message = getattr(menu, "message", None)

    def __repr__(self):
        return f"<MenuResult action={self.action!r} timed_out={self.timed_out} menu={self.menu!r}>"

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

    async def reinvoke(self):
        return await self.menu.prompt()


async def prompt(ctx: RedContext, *, content: str = None, embed: discord.Embed = None, delete_messages: bool = False,
                 timeout: float = 30.0) -> Optional[discord.Message]:
    bot: Red = ctx.bot
    message_sent = await ctx.send(content=question(content), embed=embed)
    message_recv = None
    try:
        message_recv = await bot.wait_for('message', timeout=timeout,
                                          check=lambda x: x.author == ctx.author and x.channel == ctx.channel)
    except TimeoutError:
        pass
    finally:
        if delete_messages and ctx.guild and ctx.channel.permissions_for(ctx.guild.me).manage_messages:
            if message_recv is not None:
                try:
                    await ctx.channel.delete_messages([message_sent, message_recv])
                except discord.HTTPException:
                    pass
            else:
                await message_sent.delete()
        return message_recv


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
        if ctx.guild is not None:
            perms: discord.Permissions = ctx.channel.permissions_for(ctx.guild.me)
            if not all([perms.add_reactions, perms.send_messages]):
                raise discord.Forbidden
        if len(actions.keys()) > 15:
            raise ValueError("You can only have at most up to 15 different actions")

        self.ctx = ctx
        self.bot = ctx.bot

        self.content = kwargs.get("content", None)
        self.embed = kwargs.get("embed", None)
        self.message = kwargs.get("message", None)
        if not any([self.message, self.embed, self.content, getattr(self, "_allow_empty", False)]):
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
            # otherwise, silently swallow it

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
            reaction, _ = await self.bot.wait_for("reaction_add", check=self._reaction_check, timeout=self.timeout)
        except TimeoutError:
            timed_out = True
        else:
            if reaction.emoji in self.emojis:
                ret_val = self.actions[self.emojis.index(reaction.emoji)]
        finally:
            await self._handle_post_action(False, reaction=reaction, result=ret_val)
        return MenuResult(action=ret_val, timed_out=timed_out, menu=self)


class ConfirmMenu(ReactMenu):
    def __init__(self, ctx: RedContext, default: bool = False, **kwargs):
        actions = {
            True: "\N{WHITE HEAVY CHECK MARK}",
            False: "\N{CROSS MARK}"
        }
        post_action = kwargs.pop("post_action", PostMenuAction.DELETE)

        if 'message' in kwargs:
            kwargs['content'] = kwargs.pop('message')

        super().__init__(ctx, actions, default=default, post_action=post_action,
                         post_action_check=None, **kwargs)

    async def prompt(self) -> bool:
        return (await super().prompt()).action


class PaginateMenu(ReactMenu):
    def __init__(self, ctx: RedContext, actions: Dict[Any, Union[discord.Emoji, discord.Reaction, str]],
                 pages: Sequence[Any], **kwargs):
        """Create a pagination menu

        Page switching is handled internally and any uses of the paginate buttons are not returned
        to the calling function.

        Parameters
        -----------
        ctx: RedContext
            The Red context object
        actions: Dict[Any, Union[discord.Emoji, discord.Reaction, str]]
            The list of actions to allow members to perform.
            A set of two paginate actions are always surrounding the given actions,
            however the paginate actions are handled internally and are never returned.
        pages: Sequence[Any]
            A sequence of pages. If `converter` is not given, this is expected to contain
            either strings, or objects that can be casted to strings.
        page: int
            The page index to start on. Defaults to `0`
        converter: Callable[[Any, int, int], discord.Embed]
            A converter to use to convert the items in `pages`. This defaults to a generic Embed converter
            with the item as the description with a plain 'Page {}/{}' footer.

            The call signature is as follows:

            - page_data: `Any`
            - current_page_index: `int`
            - total_pages: `int`

            This **must** return an Embed.

        message: discord.Message
            A message to re-use from prior ReactMenu executions
        member: discord.Member
            The member to listen to reactions from. Defaults to `ctx.author`
        timeout: float
            How long to wait for a reaction before timing out. Defaults to `30.0`
        """
        actions = {
            "__paginate_backward": "\N{LEFTWARDS BLACK ARROW}",
            **{x: actions[x] for x in actions},
            "__paginate_forward": "\N{BLACK RIGHTWARDS ARROW}"
        }

        self.pages = pages
        self.page = kwargs.pop("page", 0)
        self.converter = kwargs.pop("converter", lambda x, page, pages_: discord.Embed(description=str(x))
                                    .set_footer(text=f"Page {page + 1}/{pages_}"))

        self._allow_empty = True

        super().__init__(ctx, actions, post_action=PostMenuAction.REMOVE_REACTION, post_action_check=None,
                         **kwargs)

    async def prompt(self):
        result = None
        self.embed = self.converter(self.pages[self.page], self.page, len(self.pages))
        while True:
            try:
                await result.message.edit(embed=self.embed)
            except AttributeError:
                pass
            result = await super().prompt()
            print(result, self.page, len(self.pages) - 1)
            if result == "__paginate_backward":
                if self.page == 0:
                    continue
                self.page -= 1
                continue
            elif result == "__paginate_forward":
                if self.page >= len(self.pages) - 1:
                    continue
                self.page += 1
                continue
            elif result.timed_out:
                try:
                    await result.message.clear_reactions()
                except (discord.HTTPException, AttributeError):
                    pass
            return result, self.pages[self.page]
