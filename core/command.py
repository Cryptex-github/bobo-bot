import asyncio
import functools
import inspect

import discord
from discord.ext import commands

__all__ = ('BoboBotCommand', 'command')


def user_permissions_predicate(ctx):
    perms = {
        'send_messages': True,
    }
    permissions = ctx.channel.permissions_for(ctx.author)

    missing = [
        perm for perm, value in perms.items() if getattr(permissions, perm) != value
    ]

    if not missing:
        return True

    raise commands.MissingPermissions(missing)


def bot_permissions_predicate(ctx):
    perms = {
        'send_messages': True,
        'attach_files': True,
        'embed_links': True,
    }
    guild = ctx.guild
    me = guild.me if guild is not None else ctx.bot.user
    permissions = ctx.channel.permissions_for(me)

    missing = [
        perm for perm, value in perms.items() if getattr(permissions, perm) != value
    ]

    if not missing:
        return True

    raise commands.BotMissingPermissions(missing)


def hooked_wrapped_callback(command, ctx, coro):
    @functools.wraps(coro)
    async def wrapped(*args, **kwargs):
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


class BoboBotCommand(commands.Command):
    def __init__(self, func, **kwargs):
        super().__init__(func, **kwargs)

        self.checks.append(bot_permissions_predicate)
        self.checks.append(user_permissions_predicate)

    async def invoke(self, ctx):
        await self.prepare(ctx)

        # terminate the invoked_subcommand chain.
        # since we're in a regular command (and not a group) then
        # the invoked subcommand is None.
        ctx.invoked_subcommand = None
        ctx.subcommand_passed = None
        injected = hooked_wrapped_callback(self, ctx, self.callback)
        if inspect.isasyncgenfunction(injected):
            async for item in injected(*ctx.args, **ctx.kwargs):
                yield item
        else:
            yield await injected(*ctx.args, **ctx.kwargs)


def command(name=None, cls=BoboBotCommand, **attrs):
    return commands.command(name=name, cls=cls, **attrs)

command.__doc__ = commands.command.__doc__
