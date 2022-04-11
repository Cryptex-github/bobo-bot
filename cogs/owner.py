import importlib
import inspect
import textwrap
import traceback
from asyncio import create_subprocess_exec
from asyncio.subprocess import PIPE
from io import BytesIO
from typing import AsyncGenerator

import discord
import import_expression
from discord import File
from discord.ext import commands
from jishaku.codeblocks import codeblock_converter
from jishaku.exception_handling import ReactionProcedureTimer
from tabulate import tabulate  # type: ignore

from core import BoboContext, Cog, Regexs, Timer, command, unique_list
from core.types import OUTPUT_TYPE


class Owner(Cog):
    def cog_check(self, ctx: BoboContext) -> bool:
        return ctx.author.id == self.bot.owner_id
    
    @command()
    async def pull(self, ctx: BoboContext):
        proc = await create_subprocess_exec("git", "pull", stdout=PIPE, stderr=PIPE)

        stdout, stderr = await proc.communicate()

        stdout, stderr = stdout.decode(), stderr.decode()
        res = f'```\n{stdout}\n\n{stderr}```'

        files_to_reload = unique_list(Regexs.FILES_TO_RELOAD_REGEX.findall(res))

        for file_to_reload in files_to_reload:
            mod = file_to_reload.replace('/', '.').replace('.py', '')
            if mod.startswith('cogs'):
                try:
                    if mod in self.bot.extensions:
                        await self.bot.reload_extension(mod)
                    else:
                        await self.bot.load_extension(mod)
                except Exception as e:
                    res += f'\n{mod!r} failed to reload: {e}'

            try:
                lib = importlib.import_module(mod)
                importlib.reload(lib)
            except Exception as e:
                res += f'\n{mod!r} failed to reload: {e}'
        
        embed = ctx.embed(title='Pulled from Github', description=res)
        embed.add_field(name='Reloaded File(s)', value=', '.join(files_to_reload) if files_to_reload else 'No File reloaded')

        return embed
    
    @command(alias=['exe', 'exec'])
    async def execute(self, ctx: BoboContext, *, code: str) -> AsyncGenerator[OUTPUT_TYPE, None]:
        _, code = codeblock_converter(code)

        env = {
            "bot": self.bot,
            "ctx": ctx,
            "discord": discord,
            "commands": commands,
            "message": ctx.message,
            "channel": ctx.channel,
            "guild": ctx.guild,
            "author": ctx.author,
            "BytesIO": BytesIO,
            'inspect': inspect,
            'getsource': inspect.getsource,
        }

        for lib in ('asyncio', 'aiohttp'):
            env[lib] = importlib.import_module(lib)
        
        env.update(globals())
        to_execute = f'async def _execute():\n{textwrap.indent(code, " " * 4)}'

        def wrap_exception(exc: str) -> str:
            return f'error: An error occured while executing\n --> execute\n{textwrap.indent(exc, "  | ")}'

        async with ReactionProcedureTimer(ctx.message, self.bot.loop):
            try:
                import_expression.exec(to_execute, env)
            except Exception as e:
                exc = traceback.TracebackException.from_exception(e)
                yield wrap_exception(''.join(exc.format()))

            try:
                if inspect.isasyncgenfunction(to_execute):
                    async for res in to_execute(): # type: ignore
                        yield res

                    return

                result = await to_execute() # type: ignore
            except Exception as e:
                exc = traceback.TracebackException.from_exception(e)
                yield wrap_exception(''.join(exc.format()))
            else:
                if not result or result == ' ':
                    yield '\u200b'
                
                yield result
    
    @command()
    async def sql(self, ctx: BoboContext, *, query: str):
        with Timer() as timer:
            res = await self.bot.db.fetch(query)
        
        fmted = '```sql\n'

        if res:
            fmted += tabulate(res, headers='keys', tablefmt='psql') + '\n```'
        
        fmted += f'\n\n{len(res)} result(s) in {float(timer):.2f} seconds'
    
        if res <= 2000:
            return res, True
        
        return File(BytesIO(fmted.encode('utf-8')), filename='sql.txt'), True
        


setup = Owner.setup
