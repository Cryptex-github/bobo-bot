from datetime import datetime

import discord
from discord.ext import commands

from core import Cog
from core.context import BoboContext


class Listeners(Cog):
    ignore = True

    async def cog_load(self):
        if not await self.bot.redis.get('events_start_time'):
            await self.bot.redis.set('events_start_time', datetime.now().timestamp())

    @Cog.listener()
    async def on_raw_message_delete(
        self, payload: discord.RawMessageDeleteEvent
    ) -> None:
        if messages := await self.bot.delete_message_manager.get_messages(
            payload.message_id
        ):
            try:
                await self.bot.http.delete_messages(
                    payload.channel_id, messages
                )  # Well if someone were to edit their message 100 times then uhh idk.
            except (discord.Forbidden, discord.NotFound):
                for m in messages:
                    await self.bot.http.delete_message(payload.channel_id, m)

            await self.bot.delete_message_manager.delete_messages(payload.message_id)

    @Cog.listener()
    async def on_socket_event_type(self, event: str) -> None:
        await self.bot.redis.hincrby('events', event, 1)

    @Cog.listener()
    async def on_command_completion(self, ctx: BoboContext):
        if ctx.command:
            await ctx.inicrease_command_usage(ctx.command)  # type: ignore


setup = Listeners.setup
