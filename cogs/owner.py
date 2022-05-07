import importlib
import inspect
import textwrap
import traceback
from asyncio import create_subprocess_exec
from asyncio.subprocess import PIPE
from io import BytesIO
from typing import Any, AsyncGenerator

import discord
import import_expression
from discord import Embed, File
from discord.ui import View
from discord.ext import commands
from jishaku.codeblocks import codeblock_converter
from jishaku.exception_handling import ReactionProcedureTimer
from tabulate import tabulate

from core import BoboContext, Cog, Regexes, Instant, command, unique_list
from core.constants import CAN_DELETE, SAFE_SEND
from core.types import OutputType


class Owner(Cog):
    ignore = True

    async def cog_check(self, ctx: BoboContext) -> bool:
        return await self.bot.is_owner(ctx.author)

    @command()
    async def pull(self, ctx: BoboContext):
        proc = await create_subprocess_exec("git", "pull", stdout=PIPE, stderr=PIPE)

        stdout, stderr = await proc.communicate()

        stdout, stderr = stdout.decode(), stderr.decode()
        res = f'```\n{stdout}\n\n{stderr}```'

        files_to_reload = unique_list(Regexes.FILES_TO_RELOAD_REGEX.findall(res))

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
        embed.add_field(
            name='Reloaded File(s)',
            value=', '.join(files_to_reload) if files_to_reload else 'No File reloaded',
        )

        return embed

    @command(aliases=['exe', 'exec'])
    async def execute(
        self, ctx: BoboContext, *, code: str
    ) -> AsyncGenerator[OutputType, None]:
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
        _to_execute = f'async def _execute():\n{textwrap.indent(code, " " * 4)}'

        def wrap_exception(exc: str) -> str:
            return f'```py\nerror: An error occured while executing\n --> execute\n{textwrap.indent(exc, "  | ")}\n```'

        def safe_result(result: Any) -> str:
            if isinstance(result, str):
                if not result or result == ' ':
                    return '\u200b'

            if isinstance(result, (Embed, str, View, File)):
                return result

            return repr(result)

        async with ReactionProcedureTimer(ctx.message, self.bot.loop):
            try:
                import_expression.exec(_to_execute, env)
            except Exception as e:
                exc = traceback.TracebackException.from_exception(e)
                yield wrap_exception(''.join(exc.format())), SAFE_SEND, CAN_DELETE

                return

            to_execute = env['_execute']

            try:
                if inspect.isasyncgenfunction(to_execute):
                    async for res in to_execute():
                        yield safe_result(res), SAFE_SEND

                    return

                result = await to_execute()
            except Exception as e:
                exc = traceback.TracebackException.from_exception(e)
                yield wrap_exception(''.join(exc.format())), SAFE_SEND, CAN_DELETE
            else:
                if result:
                    yield safe_result(result), SAFE_SEND, CAN_DELETE

    @command()
    async def sql(self, ctx: BoboContext, *, query: str):
        with Instant() as instant:
            res = await self.bot.db.fetch(query)

        fmted = '```sql\n'

        if res:
            fmted += tabulate(res, headers='keys', tablefmt='psql') + '\n```'

        fmted += f'\n\n{len(res)} result(s) in {instant.elapsed.as_secs():.2f} seconds'

        if len(fmted) <= 2000:
            return fmted, True

        return File(BytesIO(fmted.encode('utf-8')), filename='sql.txt'), True


setup = Owner.setup
