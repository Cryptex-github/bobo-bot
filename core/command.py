from __future__ import annotations

import functools
import inspect

from typing import TYPE_CHECKING, Awaitable

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from typing import Any, AsyncGenerator, Callable, TypeVar, ParamSpec
    from core.context import BoboContext
    from core.types import OUTPUT_TYPE
    from core.cog import Cog

    P = ParamSpec('P')
    T = TypeVar('T')


__all__ = ('user_permissions_predicate', 'bot_permissions_predicate', 'command')


def user_permissions_predicate(ctx: BoboContext) -> bool:
    perms = {
        'send_messages': True,
    }

    permissions = ctx.channel.permissions_for(ctx.author) #type: ignore

    missing = [
        perm for perm, value in perms.items() if getattr(permissions, perm) != value
    ]

    if not missing:
        return True

    raise commands.MissingPermissions(missing)


def bot_permissions_predicate(ctx: BoboContext) -> bool:
    perms = {
        'send_messages': True,
        'attach_files': True,
        'embed_links': True,
    }
    guild = ctx.guild
    me = guild.me if guild is not None else ctx.bot.user
    permissions = ctx.channel.permissions_for(me) #type: ignore

    missing = [
        perm for perm, value in perms.items() if getattr(permissions, perm) != value
    ]

    if not missing:
        return True

    raise commands.BotMissingPermissions(missing)

async def process_output(ctx: BoboContext, output: OUTPUT_TYPE | None) -> None:
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

    await des(**kwargs)

async def _command_callback(ctx: BoboContext, coro: AsyncGenerator[Any, None] | Awaitable[Any]) -> None:
    if inspect.isasyncgen(coro):
        async for ret in coro: # type: ignore
            await process_output(ctx, ret)
    else:
        await process_output(ctx, await coro) # type: ignore

def command_callback(func: Callable[..., Awaitable[OUTPUT_TYPE] | AsyncGenerator[OUTPUT_TYPE, Any]]) -> Callable[..., Awaitable[OUTPUT_TYPE] | AsyncGenerator[OUTPUT_TYPE, Any]]:
    @functools.wraps(func)
    async def wrapper(self: Cog, ctx: BoboContext, *args: Any, **kwargs: Any) -> None:
        await _command_callback(ctx, func(self, ctx, *args, **kwargs))
    
    return wrapper

@discord.utils.copy_doc(commands.command)
def command(**attrs) -> Any:
    command = commands.command(**attrs)

    def wrapper(func):
        return command(command_callback(func)) # type: ignore
    
    return wrapper
