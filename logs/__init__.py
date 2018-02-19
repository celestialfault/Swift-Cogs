from redbot.core import Config
from redbot.core.bot import Red


def build_config(bot, cog):
    from .guildlog import setup as setup_guildlog
    config = Config.get_conf(cog, identifier=35908345472, force_registration=True)
    config.register_guild(**{
        "format": "EMBED",
        "ignored": False,
        "log_channels": {
            "roles": None,
            "guild": None,
            "messages": None,
            "members": None,
            "channels": None,
            "voice": None,
            "emoji": None
        },
        "roles": {
            "create": False,
            "delete": False,
            "name": False,
            "permissions": False,
            "hoist": False,
            "mention": False,
            "position": False,
            "colour": False
        },
        "guild": {
            "name": False,
            "2fa": False,
            "verification": False,
            "afk": False,
            "region": False,
            "content_filter": False,
            "owner": False
        },
        "messages": {
            "edit": False,
            "delete": False
        },
        "members": {
            "join": False,
            "leave": False,
            "name": False,
            "discriminator": False,
            "nickname": False,
            "roles": False
        },
        "channels": {
            "create": False,
            "delete": False,
            "name": False,
            "topic": False,
            "position": False,
            "category": False,
            "bitrate": False,
            "user_limit": False
        },
        "voice": {
            "channel": False,
            "selfmute": False,
            "servermute": False,
            "selfdeaf": False,
            "serverdeaf": False
        },
        "emojis": False,  # TODO: Merge this into guild logging, instead of being standalone
        "check_type": "after"
    })
    config.register_channel(ignored=False)
    config.register_member(ignored=False)
    setup_guildlog(bot, config)
    return config


async def setup(bot: Red):
    if 'OdinairLibs' not in bot.cogs:
        spec = await bot.cog_mgr.find_cog('odinair_libs')
        await bot.load_extension(spec)
    from .logs import Logs
    bot.add_cog(Logs(bot, build_config(bot, Logs)))
