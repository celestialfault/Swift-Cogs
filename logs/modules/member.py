from datetime import datetime

import discord

from redbot.core.utils.chat_formatting import inline

from logs.core import Module, LogEntry, i18n

from cog_shared.odinair_libs import td_format


class MemberModule(Module):
    name = "member"
    friendly_name = i18n("Member")
    description = i18n("Member joining, leaving, and update logging")
    settings = {
        "join": i18n("Member joining"),
        "leave": i18n("Member leaving"),
        "update": {
            "name": i18n("Member username changes"),
            "discriminator": i18n("Member discriminator changes"),
            "nickname": i18n("Member nickname changes"),
            "roles": i18n("Member role changes"),
        },
    }

    @classmethod
    def register(cls):
        pass

    @classmethod
    def unregister(cls):
        pass

    async def join(self, member: discord.Member):
        return (
            LogEntry(
                self,
                colour=discord.Color.green(),
                require_fields=False,
                description=i18n("Member {} joined\n\nAccount was created {}").format(
                    member.mention,
                    td_format(member.created_at - datetime.utcnow(), append_str=True),
                ),
            ).set_author(
                name=i18n("Member Joined"), icon_url=self.icon_uri(member)
            ).set_footer(
                text=i18n("Member ID: {}").format(member.id)
            )
        ) if await self.is_opt_enabled(
            "join"
        ) else None

    async def leave(self, member: discord.Member):
        return (
            LogEntry(
                self,
                colour=discord.Color.red(),
                require_fields=False,
                description=i18n("Member {} left").format(member.mention),
            ).set_author(
                name=i18n("Member Left"), icon_url=self.icon_uri(member)
            ).set_footer(
                text=i18n("Member ID: {}").format(member.id)
            )
        ) if await self.is_opt_enabled(
            "leave"
        ) else None

    async def update(self, before: discord.Member, after: discord.Member):
        embed = LogEntry(
            self,
            colour=discord.Color.blurple(),
            description=i18n("Member: {}").format(after.mention),
        )
        embed.set_author(name=i18n("Member Updated"), icon_url=self.icon_uri(after))
        embed.set_footer(text=i18n("Member ID: {}").format(after.id))

        return await embed.add_multiple_changed(
            before,
            after,
            [
                {"name": i18n("Username"), "value": "name", "config_opt": ["update", "name"]},
                {
                    "name": i18n("Discriminator"),
                    "value": "discriminator",
                    "config_opt": ["update", "discriminator"],
                },
                {
                    "name": i18n("Nickname"),
                    "value": "nick",
                    "converter": lambda x: x or inline(i18n("None")),
                    "config_opt": ["update", "nickname"],
                },
                {
                    "name": i18n("Roles"),
                    "value": "roles",
                    "diff": True,
                    "converter": lambda x: [str(y) for y in x if not y.is_default()],
                    "config_opt": ["update", "roles"],
                },
            ],
        )
