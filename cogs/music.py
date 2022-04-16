from __future__ import annotations

from typing import TYPE_CHECKING, cast

import magmatic

from discord import VoiceChannel, StageChannel, Member
from discord.ext.commands import guild_only

from config import LavalinkConnectionDetails

from core import Cog, command

if TYPE_CHECKING:
    from core.context import BoboContext

class Music(Cog):
    async def cog_load(self) -> None:
        if not hasattr(self.bot, 'magmatic_node'):
            self.bot.magmatic_node = self.node = magmatic.start_node(
                bot=self.bot,
                host=LavalinkConnectionDetails.host,
                port=LavalinkConnectionDetails.port,
                password=LavalinkConnectionDetails.password,
                identifier='BoboBot Lavalink Node',
                session=self.bot.session,
            )
    
    @command()
    @guild_only()
    async def join(self, ctx: BoboContext, *, channel: VoiceChannel | StageChannel | None = None) -> str:
        """Joins a voice channel."""
        author = cast(Member, ctx.author)

        if not channel:
            if not (author.voice and author.voice.channel):
                return 'You are not currently in a voice channel, nor did you provide a voice channel to join.'
            
            channel = author.voice.channel

        player = self.node.get_player(ctx.guild)

        await player.connect(channel, reconnect=True)

        return f'Joined {channel.mention}'

    @command()
    @guild_only()
    async def leave(self, ctx: BoboContext) -> str:
        """Leaves the current voice channel."""
        player = self.node.get_player(ctx.guild)

        if not player.is_connected():
            return 'I am not currently connected to a voice channel.'

        channel = player.channel

        await player.disconnect()

        return f'Left {channel.mention}'

setup = Music.setup
