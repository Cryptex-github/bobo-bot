from __future__ import annotations

from traceback import format_exc
from typing import TYPE_CHECKING

from discord.ext import commands

from core import Cog

if TYPE_CHECKING:
    from core.context import BoboContext
    from discord.ext.commands import CommandError

class ErrorHandler(Cog):
    ignore = True

    @Cog.listener()
    async def on_command_error(self, ctx: BoboContext, error: CommandError) -> None:
        async def send(content: str) -> None:
            command = f'{ctx.clean_prefix}{ctx.command.qualified_name if ctx.command else ""}'

            if '\n' in content:
                content = f'error: An error occured while executing the command\n --> {command}\n{indent(content, "  | ")}'
            else:
                content = f'error: {content}\n --> {command}'

            await ctx.send(f'```py\n{content}\nerror: Aborting due to previous error.\n```')
        
        if isinstance(error, commands.CommandNotFound):
            return

        if isinstance(error, commands.CommandOnCooldown):
            await send(f'You are on cooldown, try again in {error.retry_after:.2f} seconds.')

            return
        
        if isinstance(error, (commands.MissingPermissions, commands.BotMissingPermissions)):
            await send(f'You need the following permissions to execute this command: {", ".join(error.missing_permissions)}')

            return
        
        await send('\n' + format_exc())

setup = ErrorHandler.setup
