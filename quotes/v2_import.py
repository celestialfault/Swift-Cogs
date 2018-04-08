from datetime import datetime
from pathlib import Path

from redbot.core.utils.data_converter import DataConverter
from redbot.core import Config


def spec(v2data: dict):
    for guild_id in v2data.keys():
        parsed_quotes = []
        for quote in v2data[guild_id]:
            parsed_quotes.append({
                "guild_id": int(guild_id),
                "author_id": 0,
                "message_author_id": 0,
                "timestamp": datetime.utcnow().timestamp(),
                "text": quote["text"] if isinstance(quote, dict) else quote
            })
        yield {(Config.GUILD, guild_id): {('quotes',): parsed_quotes}}


async def import_v2_data(path: Path, config: Config):
    await DataConverter(config).convert(path, spec)
