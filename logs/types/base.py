from logs.guildlog import GuildLog


class LogType:
    """Common base for log types"""
    name = "base"

    def __init__(self, guild: GuildLog):
        self.guild = guild

    async def update(self, before, after, **kwargs):
        raise NotImplementedError

    async def create(self, created, **kwargs):
        raise NotImplementedError

    async def delete(self, deleted, **kwargs):
        raise NotImplementedError
