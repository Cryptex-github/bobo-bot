from __future__ import annotations

import asyncio
import logging
import os
from typing import TYPE_CHECKING, NamedTuple, Type

import aiohttp
import asyncpg
import discord
import jishaku
import mystbin
from discord.utils import MISSING
from discord.ext import commands
from discord.ext.commands.cooldowns import MaxConcurrency
from requests_html import AsyncHTMLSession

from core.cache_manager import DeleteMessageManager
from core.utils import Timer
from core.cdn import CDNClient

jishaku.Flags.NO_UNDERSCORE = True
jishaku.Flags.NO_DM_TRACEBACK = True

from config import DbConnectionDetails, token

from .context import BoboContext

if TYPE_CHECKING:
    from discord import Interaction, Message
    from discord.ext.commands import Command
    from discord.ext.commands._types import ContextT

    from magmatic import Node

__log__ = logging.getLogger('BoboBot')
__all__ = ('BoboBot',)


class SelfTestResult(NamedTuple):
    postgres: float
    redis: float
    discord_rest: float
    discord_ws: float


class BoboBot(commands.Bot):
    if TYPE_CHECKING:
        magmatic_node: Node

    def __init__(self) -> None:
        self.logger = __log__

        intents = discord.Intents.all()

        super().__init__(
            command_prefix='bobo ',
            intents=intents,
            description='Bobo Bot, The Anime Bot but better.',
            chunk_guilds_at_startup=False,
            case_insensitive=True,
            allowed_mentions=discord.AllowedMentions.none(),
            strip_after_prefix=True,
        )

    async def self_test(self) -> SelfTestResult:
        with Timer() as postgres_timer:
            await self.db.execute('SELECT 1')

        with Timer() as redis_timer:
            await self.redis.ping()

        with Timer() as discord_rest_timer:
            await self.http.get_gateway()

        r = lambda x: round(x, 3)

        return SelfTestResult(
            r(float(postgres_timer) * 1000),
            r(float(redis_timer) * 1000),
            r(float(discord_rest_timer) * 1000),
            r(float(self.latency) * 1000),
        )

    async def getch(self, object_: str, id_: int) -> discord.abc.Snowflake:
        get = getattr(self, f'get_{object_}')
        fetch = getattr(self, f'fetch_{object_}')

        obj = await get(id_)

        if not obj:
            obj = await fetch(id_)

        return obj

    def initialize_libaries(self) -> None:
        self.context = BoboContext
        self.mystbin = mystbin.Client(session=self.session)
        self.html_session = AsyncHTMLSession()
        self.cdn = CDNClient(self)

    async def initialize_constants(self) -> None:
        self.color = 0xFF4500
        self.session = aiohttp.ClientSession(connector=self.connector)

        from redis import asyncio as aioredis

        self.redis = aioredis.from_url('redis://127.0.0.1', decode_responses=True)
        self.delete_message_manager = DeleteMessageManager(self.redis)

        self.ready_once = False

    def add_command(self, command: Command) -> None:
        ignore_list = ('help',)

        super().add_command(command)
        command.cooldown_after_parsing = True

        if not getattr(command._buckets, '_cooldown', None):
            command._buckets = commands.CooldownMapping.from_cooldown(
                1, 2, commands.BucketType.user
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
        from core.web import app

        await self.initialize_constants()
        self.initialize_libaries()

        self.db = await asyncpg.create_pool(
            host=DbConnectionDetails.host,
            user=DbConnectionDetails.user,
            password=DbConnectionDetails.password,
            database=DbConnectionDetails.database,
        )

        await self.load_all_extensions()

        self.web = app

        app.bot = self

        self.web_task = self.loop.create_task(app.run_task(host='0.0.0.0', port=8082))

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
        super().run(token=token)
