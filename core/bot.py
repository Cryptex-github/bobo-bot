from collections import Counter
import inspect
import logging
import os

import aiohttp
import asyncpg
from discord.ext.commands.cooldowns import MaxConcurrency
from core.command import BoboBotCommand
import mystbin
import discord
from discord.ext import commands

import jishaku

jishaku.Flags.NO_UNDERSCORE = True
jishaku.Flags.NO_DM_TRACEBACK = True

from .context import BoboContext
from config import DbConnectionDetails, token

__log__ = logging.getLogger('BoboBot')
__all__ = ('BoboBot',)


class BoboBot(commands.Bot):
    def __init__(self):
        self.connector = aiohttp.TCPConnector(limit=200)
        self.logger = __log__
        
        intents = discord.Intents.all()

        super().__init__(
            connector=self.connector,
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
                if not await self.can_run(ctx, call_once=True):
                    raise commands.CheckFailure(
                        'The global check once functions failed.'
                    )
                if isinstance(ctx.command, BoboBotCommand):
                    async for m in ctx.command.invoke(ctx):
                        await self.process_output(ctx, m)
                else:
                    await ctx.command.invoke(ctx)
            except commands.CommandError as exc:
                await ctx.command.dispatch_error(ctx, exc)
            else:
                self.dispatch('command_completion', ctx)
        elif ctx.invoked_with:
            exc = commands.CommandNotFound(f'Command "{ctx.invoked_with}" is not found')  # type: ignore
            self.dispatch('command_error', ctx, exc)
    
    async def process_output(self, ctx, output):
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
                kwargs |= i

        if i is True:
            des = ctx.reply

        await des(**kwargs)

    async def getch(self, /, id: int) -> discord.User:
        return self.get_user(id) or await self.fetch_user(id)

    def initialize_libaries(self):
        self.context = BoboContext
        self.mystbin = mystbin.Client(session=self.session)
    
    async def initialize_constants(self):
        self.color = 0xFF4500
        self.session = aiohttp.ClientSession(connector=self.connector)

    def add_command(self, command):
        super().add_command(command)
        command.cooldown_after_parsing = True

        if not getattr(command._buckets, '_cooldown', None):
            command._buckets = commands.CooldownMapping.from_cooldown(
                1, 3, commands.BucketType.user
            )

        if command._max_concurrency is None:
            command._max_concurrency = MaxConcurrency(
                1, per=commands.BucketType.user, wait=False
            )

    async def setup(self):
        await self.initialize_constants()
        self.initialize_libaries()

        self.db = await asyncpg.create_pool(
            host=DbConnectionDetails.host,
            user=DbConnectionDetails.user,
            password=DbConnectionDetails.password,
            database=DbConnectionDetails.database,
        )
    
    def load_all_extensions(self):
        for file in os.listdir('./cogs'):
            if file.endswith('.py'):
                try:
                    self.load_extension(f'cogs.{file[:-3]}')
                except Exception as e:
                    self.logger.critical(
                        f'Unable to load extension: {file}, ignoring. Exception: {e}'
                    )
        self.load_extension('jishaku')

    async def get_context(self, message, *, cls=None):
        return await super().get_context(message, cls=self.context)

    def unload_all_extensions(self):
        for file in os.listdir('./cogs'):
            if file.endswith('.py'):
                try:
                    self.unload_extension(f'cogs.{file[:-3]}')
                except Exception as e:
                    self.logger.critical(
                        f'Unable to unload extension: {file}, ignoring. Exception: {e}'
                    )
        self.unload_extension('jishaku')
    
    async def close(self):
        self.unload_all_extensions()
        await self.db.close()
        await self.session.close()
        
        await super().close()

    def run(self):
        self.load_all_extensions()
        self.loop.run_until_complete(self.setup())
        super().run(token=token)
