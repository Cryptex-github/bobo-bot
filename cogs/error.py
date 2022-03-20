from __future__ import annotations

from traceback import format_exc
from typing import TYPE_CHECKING

from discord.ext import commands

from core import Cog

if TYPE_CHECKING:
    from core.context import BoboContext
    from discord.ext.commands import CommandError

class ErrorHandler(Cog):
    @Cog.listener()
    async def on_command_error(self, ctx: BoboContext, error: CommandError) -> None:
        send = lambda x: ctx.send(f'```Err({x})\nAborting due to previous error.\n```')

        if isinstance(error, commands.CommandOnCooldown):
            await send(f'You are on cooldown, try again in {error.retry_after:.2f} seconds.')

            return
        
        if isinstance(error, (commands.MissingPermissions, commands.BotMissingPermissions)):
            await send(f'You need the following permissions to execute this command: {", ".join(error.missing_permissions)}')

            return
        
        await send(format_exc())

setup = ErrorHandler.setup
