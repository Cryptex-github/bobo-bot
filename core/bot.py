from __future__ import annotations

import logging
import os
from collections import namedtuple
from typing import TYPE_CHECKING, NamedTuple

import aiohttp
import aioredis
import asyncpg
import discord
import jishaku
import mystbin
import uvloop
from discord.ext import commands
from discord.ext.commands.cooldowns import MaxConcurrency
from requests_html import AsyncHTMLSession

from core.cache_manager import DeleteMessageManager
from core.command import BoboBotCommand
from core.utils import Timer

if TYPE_CHECKING:
    from core import OUTPUT_TYPE
    from .cog import Cog

jishaku.Flags.NO_UNDERSCORE = True
jishaku.Flags.NO_DM_TRACEBACK = True

from config import DbConnectionDetails, token

from .context import BoboContext

__log__ = logging.getLogger('BoboBot')
__all__ = ('BoboBot',)


# @discord.utils.copy_doc(commands.bot.BotBase)
# class BotBase(commands.bot.GroupMixin[Cog]):
#     ...


# @discord.utils.copy_doc(commands.Bot)
class BoboBot(commands.Bot):
    def __init__(self):
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

    @discord.utils.copy_doc(commands.Bot.invoke)
    async def invoke(self, ctx):
        if ctx.command is not None:
            self.dispatch('command', ctx)
            try:
                if await self.can_run(ctx, call_once=True):
                    if isinstance(ctx.command, BoboBotCommand):
                        async for m in ctx.command.invoke(ctx):  # type: ignore
                            await self.process_output(ctx, m)  # type: ignore
                    else:
                        await self.process_output(ctx, await c)
                else:
                    raise commands.CheckFailure(
                        'The global check once functions failed.'
                    )
            except commands.CommandError as exc:
                await ctx.command.dispatch_error(ctx, exc)
            else:
                self.dispatch('command_completion', ctx)
        elif ctx.invoked_with:
            exc = commands.CommandNotFound(f'Command "{ctx.invoked_with}" is not found')  # type: ignore
            self.dispatch('command_error', ctx, exc)
    
    async def self_test(self, ctx: BoboContext | None = None) -> NamedTuple:
        with Timer() as postgres_timer:
            await self.db.execute('SELECT 1')
        
        with Timer() as redis_timer:
            await self.redis.ping()
        
        with Timer() as discord_rest_timer:
            if ctx:
                await ctx.channel.trigger_typing()
            else:
                if user := self.user:
                    await self.http.get_user(user.id)
        
        res = namedtuple('SelfTestResult', 'postgres redis discord_rest discord_ws')
        
        r = lambda x: round(x, 3)

        return res(r(float(postgres_timer) * 1000), r(float(redis_timer) * 1000), r(float(discord_rest_timer) * 1000), r(float(self.latency) * 1000))
        

    async def process_output(self, ctx: BoboContext, output: OUTPUT_TYPE | None) -> None:
        if output is None:
            return

        kwargs = {}
        des = ctx.send

        if not isinstance(output, tuple):
            output = (output,)

        for i in output:
            if isinstance(i, discord.Embed):
                kwargs['embed'] = i

            elif isinstance(i, str):
                kwargs['content'] = i

            elif isinstance(i, discord.File):
                kwargs['file'] = i

            elif isinstance(i, dict):
                kwargs.update(i)
        
        try:
            if i is True: # type: ignore
                des = ctx.reply
        except NameError:
            pass

        if c := kwargs.pop('content'):
            await des(content=c, **kwargs)

    async def getch(self, /, id: int) -> discord.User:
        user = self.get_user(id)
        if not user:
            user = await self.fetch_user(id)

        return user

    def initialize_libaries(self):
        self.context = BoboContext
        self.mystbin = mystbin.Client(session=self.session)
        self.html_session = AsyncHTMLSession()
    
    async def initialize_constants(self):
        self.color = 0xFF4500
        self.session = aiohttp.ClientSession(connector=self.connector)

        self.redis = aioredis.from_url('redis://localhost', decode_responses=True)
        self.delete_message_manager = DeleteMessageManager(self.redis)

    def add_command(self, command):
        ignore_list = ('help',)

        super().add_command(command)
        command.cooldown_after_parsing = True

        if not getattr(command._buckets, '_cooldown', None):
            command._buckets = commands.CooldownMapping.from_cooldown(
                1, 3, commands.BucketType.user
            )

        if command._max_concurrency is None and command.qualified_name not in ignore_list:
            command._max_concurrency = MaxConcurrency(
                1, per=commands.BucketType.user, wait=False
            )
    
    async def _async_setup_hook(self):
        loop = asyncio.get_running_loop()
        self.connector = aiohttp.TCPConnector(limit=0, loop=loop)
        self.http.connector = self.connector

        await super()._async_setup_hook()

    async def setup_hook(self):
        await self.initialize_constants()
        self.initialize_libaries()

        self.db = await asyncpg.create_pool(
            host=DbConnectionDetails.host,
            user=DbConnectionDetails.user,
            password=DbConnectionDetails.password,
            database=DbConnectionDetails.database,
        )
        
        await self.load_all_extensions()
    
    async def load_all_extensions(self):
        for file in os.listdir('./cogs'):
            if file.endswith('.py'):
                try:
                    await self.load_extension(f'cogs.{file[:-3]}')
                except Exception as e:
                    self.logger.critical(
                        f'Unable to load extension: {file}, ignoring. Exception: {e}'
                    )
        await self.load_extension('jishaku')

    async def get_context(self, message, *, cls=None):
        return await super().get_context(message, cls=self.context)

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
    
    async def close(self):
        tasks = [
            self.unload_all_extensions(),
            self.db.close(),
            self.session.close(),
            self.redis.close(),
            self.html_session.close()
        ]


        await asyncio.gather(*tasks)
        
        await super().close()

    def run(self):
        super().run(token=token)
