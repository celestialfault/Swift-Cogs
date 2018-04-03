from datetime import datetime
from pathlib import Path

from discord import AppInfo

from redbot.core.utils.data_converter import DataConverter
from redbot.core import Config


async def import_v2_data(path: Path, config: Config, appinfo: AppInfo):
    converter = DataConverter(config)

    def spec(v2data: dict):
        for guild_id in v2data.keys():
            parsed_quotes = []
            for quote in v2data[guild_id]:
                parsed_quotes.append({
                    "guild_id": int(guild_id),
                    "author_id": getattr(appinfo.owner, "id", None),
                    "message_author_id": None,
                    "timestamp": datetime.utcnow().timestamp(),
                    "text": quote["text"] if isinstance(quote, dict) else quote
                })
            yield {(Config.GUILD, guild_id): {('quotes',): parsed_quotes}}

    await converter.convert(path, spec)
