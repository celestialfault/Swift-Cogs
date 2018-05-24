from redbot.core import Config
from redbot.core.i18n import Translator

i18n = Translator("YTFeeds", __file__)

config = Config.get_conf(None, cog_name="YTFeeds", identifier=2342355123)
config.register_custom("FEED", last_video=0, channels=[])
config.register_guild(message=i18n("**{channel.name}** has uploaded a new video!"))
