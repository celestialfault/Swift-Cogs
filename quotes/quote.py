from redbot.core.bot import Red
from datetime import datetime


class Quote:
    """
    This is almost definitely a gross misuse of classes.
    """

    def __init__(self, bot: Red, **kwargs):
        self.guild = bot.get_guild(kwargs["guild_id"])
        self.author = self.guild.get_member(kwargs["author_id"])
        self.message_author = self.guild.get_member(kwargs["message_author_id"])
        self.text = kwargs["text"]
        self.id = kwargs.get("id", -1)
        self.timestamp = datetime.fromtimestamp(kwargs.get("timestamp", 0))
