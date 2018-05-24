from collections import namedtuple
from datetime import datetime, timedelta
from typing import Dict, Optional
import logging

import aiohttp
import discord
from lxml import etree

from cog_shared.swift_libs import trim_to
from ytfeed.config import config, i18n

session = aiohttp.ClientSession()
log = logging.getLogger("red.ytfeed")


Channel = namedtuple("Channel", ["name", "id", "url"])


class Video:

    def __init__(self, channel: Channel, xml_tree):
        self.channel = channel
        # noinspection PyProtectedMember
        self.tree: etree._Element = xml_tree

    def embed(self, colour: discord.Colour = discord.Color.default()):
        return (
            discord.Embed(
                colour=colour,
                description=trim_to(self.description, 1000),
                url=self.url,
                title=self.title,
                timestamp=self.timestamp,
            )
            .set_author(name=self.channel.name, url=self.channel.url)
            .set_image(url=self.thumbnail or discord.Embed.Empty)
            .set_footer(text=i18n("{:,} views").format(self.views))
        )

    @property
    def timestamp(self) -> datetime:
        # I'm not sure if the +00:00 is important here or if it's the same all the time,
        # so I'm just putting it here to be safe (and so this actually parses)
        return datetime.strptime(self.tree[6].text, "%Y-%m-%dT%H:%M:%S+00:00")

    @property
    def author(self) -> Dict[str, str]:
        return {"name": self.tree[5][0].text, "url": self.tree[5][1].text}

    @property
    def url(self) -> str:
        return self.tree[4].get("href")

    @property
    def title(self) -> str:
        return self.tree[3].text

    @property
    def thumbnail(self) -> Optional[str]:
        try:
            return self.tree[8][2].get("url")
        except IndexError:
            return None

    @property
    def description(self) -> Optional[str]:
        try:
            return self.tree[8][3].text
        except IndexError:
            return None

    @property
    def views(self) -> int:
        try:
            return int(self.tree[8][4][1].get("views"))
        except ValueError:
            return 0


class Feed:

    def __init__(self, channel_id: str):
        self.url = parse_rss_url(channel_id)
        self.cid = channel_id
        self.last_fetched: Optional[datetime] = None
        self.last_post: Optional[datetime] = None
        # noinspection PyProtectedMember
        self.cache: Optional[etree._Element] = None
        self.channel: Optional[Channel] = None

    @property
    def conf(self):
        return config.custom("FEED", self.cid)

    async def _get_feed(self) -> etree.Element:
        log.debug(f"getting rss feed for channel {self.cid}")
        if self.cache is not None and (self.last_fetched or datetime.utcfromtimestamp(0)) < (
            datetime.utcnow() - timedelta(minutes=30)
        ):
            return self.cache
        async with session.get(self.url) as response:
            response: aiohttp.ClientResponse = response
            if not str(response.status).startswith("2"):
                raise RuntimeError("response status is not equal to 200")
            xml = etree.fromstring((await response.text()).encode("utf-8"))
            self.cache = xml
            self.last_fetched = datetime.utcnow()
            return xml

    async def resolve(self):
        xml = await self._get_feed()
        channel = Channel(name=xml[3].text, url=xml[4].get("href"), id=xml[2].text)
        self.channel = channel
        return {
            "channel": channel,
            "videos": list(sorted((Video(channel, x) for x in xml[7:]), key=lambda x: x.timestamp)),
        }

    @classmethod
    async def all_feeds(cls):
        feeds = await config.custom("FEED")()
        for channel_id, feed_data in feeds.items():
            yield cls(channel_id)


def parse_rss_url(channel_id: str) -> str:
    return f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
