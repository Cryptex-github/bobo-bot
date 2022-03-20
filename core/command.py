from __future__ import annotations

import asyncio
import functools
import inspect

from typing import TYPE_CHECKING

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from typing import Any, AsyncGenerator, Callable, TypeVar, ParamSpec
    from core.context import BoboContext
    from core.types import OUTPUT_TYPE
    from core.cog import Cog

    P = ParamSpec('P')
    T = TypeVar('T')


__all__ = ('BoboBotCommand', 'command')


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


def hooked_wrapped_callback(command, ctx: BoboContext, coro: Callable[[Any], Any]) -> Callable[[Any, Any], AsyncGenerator[OUTPUT_TYPE, None]]:
    @functools.wraps(coro)
    async def wrapped(*args: Any, **kwargs: Any) -> AsyncGenerator[OUTPUT_TYPE, None]:
        try:
            if inspect.isasyncgenfunction(coro):
                async for ret in coro(*args, **kwargs):
                    yield ret
            else:
                yield await coro(*args, **kwargs)
        except commands.CommandError:
            ctx.command_failed = True
            raise
        except asyncio.CancelledError:
            ctx.command_failed = True
            return
        except Exception as exc:
            ctx.command_failed = True
            raise commands.CommandInvokeError(exc) from exc
        finally:
            if command._max_concurrency is not None:
                await command._max_concurrency.release(ctx)

            await command.call_after_hooks(ctx)

    return wrapped


class BoboBotCommand(commands.Command[Cog, P, T]):
    def __init__(self, func: Any, **kwargs: Any) -> None:
        super().__init__(func, **kwargs)

        self.checks.append(bot_permissions_predicate) #type: ignore
        self.checks.append(user_permissions_predicate) #type: ignore

    async def invoke(self, ctx: BoboContext) -> AsyncGenerator[OUTPUT_TYPE, None]:
        await self.prepare(ctx)  # type: ignore

        # terminate the invoked_subcommand chain.
        # since we're in a regular command (and not a group) then
        # the invoked subcommand is None.
        ctx.invoked_subcommand = None
        ctx.subcommand_passed = None
        injected = hooked_wrapped_callback(self, ctx, self.callback) #type: ignore
        async for item in injected(*ctx.args, **ctx.kwargs):
            yield item


class Group(commands.Group):
    def command(self, *args: Any, **kwargs: Any) -> Any:
        if 'cls' not in kwargs:
            kwargs['cls'] = BoboBotCommand
        
        return super().command(*args, **kwargs)


@discord.utils.copy_doc(commands.command)
def command(name=None, cls=BoboBotCommand, **attrs) -> Any:
    return commands.command(name=name, cls=cls, **attrs)
