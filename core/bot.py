from __future__ import annotations

import asyncio
import logging
import os
import sys
from typing import TYPE_CHECKING, NamedTuple, Type

import aiohttp
import redis.asyncio as aioredis
import asyncpg
import discord
import jishaku
import mystbin
from discord.utils import MISSING
from discord.ext import commands
from discord.ext.commands.cooldowns import MaxConcurrency
from requests_html import AsyncHTMLSession

from core.cache_manager import DeleteMessageManager
from core.utils import Instant
from core.cdn import CDNClient
from core.constants import BETA_ID

jishaku.Flags.NO_UNDERSCORE = True
jishaku.Flags.NO_DM_TRACEBACK = True

from config import DbConnectionDetails, token, prod_token

from .context import BoboContext

if TYPE_CHECKING:
    from discord import Interaction, Message
    from discord.ext.commands import Command
    from discord.ext.commands._types import ContextT

    from magmatic import Node

discord_logger = logging.getLogger('discord')
discord_logger.setLevel(logging.INFO)

__log__ = logging.getLogger('BoboBot')
__all__ = ('BoboBot',)

logging_handler = logging.StreamHandler()
logging_handler.setFormatter(
    logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s')
)

discord_logger.addHandler(logging_handler)
__log__.addHandler(logging_handler)


class SelfTestResult(NamedTuple):
    postgres: float
    redis: float
    discord_rest: float
    discord_ws: float
    bobo_api: float
    bobo_cdn: float
    bobo_eval_api: float


class BoboBot(commands.Bot):
    if TYPE_CHECKING:
        magmatic_node: Node

    def __init__(self) -> None:
        self.logger = __log__

        intents = discord.Intents.all()

        super().__init__(
            command_prefix=self._get_prefix,
            intents=intents,
            description='Bobo Bot, The Anime Bot but better.',
            chunk_guilds_at_startup=False,
            case_insensitive=True,
            allowed_mentions=discord.AllowedMentions.none(),
            strip_after_prefix=True,
        )

    @staticmethod
    def _get_prefix(bot: BoboBot, message: Message) -> str:
        if not bot.user or bot.user.id == BETA_ID:
            return 'bobo '

        return 'bobob '

    async def _test_latency(self, url: str) -> Instant:
        with Instant() as instant:
            async with self.session.get(url) as _:
                ...

        return instant

    async def self_test(self) -> SelfTestResult:
        with Instant() as postgres_instant:
            await self.db.execute('SELECT 1')

        with Instant() as redis_instant:
            await self.redis.ping()

        (
            discord_rest_instant,
            bobo_api_instant,
            bobo_cdn_instant,
            bobo_eval_api_instant,
        ) = await asyncio.gather(
            self._test_latency('https://discord.com/api/v10'),
            self._test_latency('https://api.bobobot.cf'),
            self._test_latency('https://cdn.bobobot.cf'),
            self._test_latency('https://eval.bobobot.cf'),
        )

        r = lambda x: round(x, 3)

        return SelfTestResult(
            r(postgres_instant.elapsed.as_millis()),
            r(redis_instant.elapsed.as_millis()),
            r(discord_rest_instant.elapsed.as_millis()),
            r(bobo_api_instant.elapsed.as_millis()),
            r(bobo_cdn_instant.elapsed.as_millis()),
            r(bobo_eval_api_instant.elapsed.as_millis()),
            r(float(self.latency) * 1000),
        )

    async def getch(self, object_: str, id_: int) -> discord.abc.Snowflake:
        get = getattr(self, f'get_{object_}')
        fetch = getattr(self, f'fetch_{object_}')

        obj = get(id_)

        if not obj:
            obj = await fetch(id_)

        return obj

    async def initialize(self) -> None:
        from core.web import app

        self.session = aiohttp.ClientSession(connector=self.connector)
        self.ready_once = False
        self.context = BoboContext
        self.mystbin = mystbin.Client(session=self.session)
        self.html_session = AsyncHTMLSession()
        self.cdn = CDNClient(self)

        self.redis = aioredis.from_url(
            'unix:///var/run/redis/redis-server.sock', decode_responses=True
        )
        self.delete_message_manager = DeleteMessageManager(self.redis)

        self.db = await asyncpg.create_pool(
            host=DbConnectionDetails.host,
            user=DbConnectionDetails.user,
            password=DbConnectionDetails.password,
            database=DbConnectionDetails.database,
        )

        await self.redis.ping()
        await self.load_all_extensions()

        self.web = app
        app.bot = self

        self.web_task = self.loop.create_task(
            app.run_task(host='0.0.0.0', port=8082, use_reloader=False)
        )

    def get_cooldown(self, message: Message) -> commands.Cooldown | None:
        if message.author.id == 590323594744168494:
            return

        return commands.Cooldown(1, 2)

    def add_command(self, command: Command) -> None:
        ignore_list = ('help',)

        super().add_command(command)
        command.cooldown_after_parsing = True

        if not getattr(command._buckets, '_cooldown', None):
            command._buckets = commands.DynamicCooldownMapping(
                self.get_cooldown, commands.BucketType.user
            )

        if (
            command._max_concurrency is None
            and command.qualified_name not in ignore_list
        ):
            command._max_concurrency = MaxConcurrency(
                2, per=commands.BucketType.user, wait=False
            )

    async def _async_setup_hook(self) -> None:
        loop = asyncio.get_running_loop()
        self.connector = aiohttp.TCPConnector(limit=0, loop=loop)
        self.http.connector = self.connector

        await super()._async_setup_hook()

    async def on_ready(self) -> None:
        if self.ready_once:
            return

        self.ready_once = True
        self.dispatch('ready_once')

    async def on_ready_once(self) -> None:
        chunk_tasks = []

        for guild in self.guilds:
            if not guild.chunked:
                chunk_tasks.append(guild.chunk())

        await asyncio.gather(*chunk_tasks)

    async def setup_hook(self) -> None:
        await self.initialize()

    async def load_all_extensions(self) -> None:
        for file in os.listdir('./cogs'):
            if file.endswith('.py'):
                try:
                    await self.load_extension(f'cogs.{file[:-3]}')
                except Exception as e:
                    self.logger.critical(
                        f'Unable to load extension: {file}, ignoring. Exception: {e}'
                    )
        await self.load_extension('jishaku')

    async def get_context(
        self, origin: Message | Interaction, *, cls: Type[ContextT] = MISSING
    ):
        return await super().get_context(origin, cls=self.context)

    async def unload_all_extensions(self):
        for file in os.listdir('./cogs'):
            if file.endswith('.py'):
                try:
                    await self.unload_extension(f'cogs.{file[:-3]}')
                except Exception as e:
                    self.logger.critical(
                        f'Unable to unload extension: {file}, ignoring. Exception: {e}'
                    )

        await self.unload_extension('jishaku')

    async def close(self) -> None:
        tasks = [
            self.unload_all_extensions(),
            self.db.close(),
            self.session.close(),
            self.redis.close(),
            self.html_session.close(),
            self.web.shutdown(),
        ]

        await asyncio.gather(*tasks)
        await self.web_task

        await super().close()

    def run(self) -> None:
        try:
            mode = sys.argv[1]
        except IndexError:
            mode = 'dev'

        if mode == 'dev':
            super().run(token=token)
        else:
            super().run(token=prod_token)
