from __future__ import annotations

from typing import TYPE_CHECKING
from textwrap import dedent

from core import Cog, command

if TYPE_CHECKING:
    from core import BoboContext

class Misc(Cog):
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

setup = Misc.setup
