from __future__ import annotations

from typing import TYPE_CHECKING

from discord.ext.commands import guild_only
from core import Cog
from core.command import group

if TYPE_CHECKING:
    from discord import Embed

    from core.context import BoboContext


class Settings(Cog):
    @group()
    @guild_only()
    async def prefix(self, ctx: BoboContext) -> Embed | str:
        assert ctx.guild is not None

        prefix = await self.bot.prefix_manager.get_prefix(ctx.guild.id)

        if not prefix:
            return 'No custom prefix has been set.'

        return ctx.embed(title='Prefixes', description='\n'.join(prefix)).set_author(
            name=ctx.guild.name, icon_url=getattr(ctx.guild, 'icon', None)
        )

    @prefix.command()
    @guild_only()
    async def add(self, ctx: BoboContext, *prefixes: str) -> str:
        assert ctx.guild is not None

        await self.bot.prefix_manager.add_prefix(ctx.guild.id, *prefixes)

        return 'Added prefixes.'

    @prefix.command()
    @guild_only()
    async def remove(self, ctx: BoboContext, *prefixes: str) -> str:
        assert ctx.guild is not None

        await self.bot.prefix_manager.remove_prefixes(ctx.guild.id, *prefixes)

        return 'Removed prefixes.'

    @prefix.command()
    @guild_only()
    async def reset(self, ctx: BoboContext) -> str:
        assert ctx.guild is not None

        await self.bot.prefix_manager.reset_prefix(ctx.guild.id)

        return 'Reset prefixes, the only prefix is now the default prefix.'


setup = Settings.setup
