from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from textwrap import dedent

from core import Cog, command

if TYPE_CHECKING:
    from core import BoboContext

class Misc(Cog):
    async def cog_load(self) -> None:
        with open('./events.lua', 'r') as f:
            self.get_event_counts = self.redis.register_script(f.read())

    @command()
    async def ping(self, ctx: BoboContext) -> str:
        """Pong!"""
        res = await self.bot.self_test()

        return dedent(f"""
            PostgreSQL latency: {res.postgres}ms
            Redis latency: {res.redis}ms
            Discord REST latency: {res.discord_rest}ms
            Discord WS latency: {res.discord_ws}ms
        """)
    
    @command()
    async def events(self, ctx: BoboContext) -> str:
        """Events"""
        events_count = await self.get_event_counts()

        time_difference = (int(datetime.now().timestamp()) - int(await self.redis.get('events_start_time'))) / 60

        return dedent(f"""
            Total WS Events: {events_count}
            Average WS Events per minute: {events_count // time_difference}
        """)

setup = Misc.setup
