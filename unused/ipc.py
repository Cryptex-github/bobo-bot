from __future__ import annotations

from typing import TYPE_CHECKING
from datetime import datetime

from core.cog import Cog
from cogs.misc import Misc
from redisipc import IPC as RedisIPC

if TYPE_CHECKING:
    from core.bot import BoboBot
    from core.types import Json


class IPC(Cog, RedisIPC):
    def __init__(self, bot: BoboBot) -> None:
        super().__init__(bot)

        RedisIPC.__init__(self, bot.redis, channel='ipc:bobobot')
    
    async def cog_load(self) -> None:
        self._task = self.bot.loop.create_task(self.start())
    
    async def cog_unload(self) -> None:
        await self.close()

        self._task.cancel()
        await self._task

    async def handle_stats(self) -> Json:
        async with self.bot.db.acquire() as conn:
            total_command_uses = await conn.fetchval('SELECT SUM(uses) FROM commands_usage')
            most_used_command = await conn.fetchval(
                'SELECT command FROM commands_usage ORDER BY uses DESC LIMIT 1'
            )

        latency = await self.bot.self_test()

        misc = self.bot.get_cog('Misc')

        if isinstance(misc, Misc):
            events = await misc.get_event_counts()
        else:
            events = 0

        time_difference = (
            float(datetime.now().timestamp())
            - float(await self.bot.redis.get('events_start_time'))
        ) / 60

        return {
            'Servers': len(self.bot.guilds),
            'Users': len(self.bot.users),
            'Channels': len(list(self.bot.get_all_channels())),
            'Commands': len(list(self.bot.walk_commands())),
            'Total Command Uses': int(total_command_uses),
            'Most Used Command': most_used_command,
            'Postgres Latency': f'{latency.postgres} ms',
            'Redis Latency': f'{latency.redis} ms',
            'Discord REST Latency': f'{latency.discord_rest} ms',
            'Discord WebSocket Latency': f'{latency.discord_ws} ms',
            'Total Gateway Events': f'{events:,}',
            'Average Events per minute': f'{events // time_difference}',
        }

    async def handle_commands(self) -> Json:
        json = []

        for command in self.bot.walk_commands():
            cooldown_fmted = None

            if bucket := getattr(command, '_buckets'):
                if cooldown := getattr(bucket, '_cooldown'):
                    cooldown_fmted = f'{cooldown.rate} time(s) per {cooldown.per} second(s)'

            json.append(
                {
                    'name': command.qualified_name,
                    'args': command.signature,
                    'category': command.cog_name,
                    'description': (
                        command.description or command.short_doc or 'No Help Provided'
                    ),
                    'aliases': command.aliases,
                    'cooldown': cooldown_fmted,
                }
            )

        cogs = [
            cog.qualified_name
            for cog in self.bot.cogs.values()
            if not getattr(cog, 'ignore', False)
        ]
        del cogs[cogs.index('Jishaku')]

        return {'commands': json, 'categories': cogs} # type: ignore

setup = IPC.setup
