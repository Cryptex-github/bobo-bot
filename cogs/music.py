from __future__ import annotations

from typing import TYPE_CHECKING

import magmatic
from magmatic import Source, Playlist

from discord import VoiceChannel, StageChannel, Member

from config import LavalinkConnectionDetails

from core import Cog, command

if TYPE_CHECKING:
    from core.context import BoboContext


class Music(Cog):
    async def cog_load(self) -> None:
        if not hasattr(self.bot, 'magmatic_node'):
            self.bot.magmatic_node = self.node = await magmatic.start_node(
                bot=self.bot,
                host=LavalinkConnectionDetails.host,
                port=LavalinkConnectionDetails.port,
                password=LavalinkConnectionDetails.password,
                resume=False,
                identifier='BoboBot Lavalink Node',
                session=self.bot.session,
            )

    async def cog_check(self, ctx: BoboContext) -> bool:
        if not ctx.guild:
            return False

        if ctx.invoked_with in ('join', 'leave'):
            return True

        player = self.node.get_player(ctx.guild)

        if not player.is_connected():
            await ctx.send('I am not connected to any voice channel.')

            return False

        return True

    @command(aliases=['connect'])
    async def join(
        self, ctx: BoboContext, *, channel: VoiceChannel | StageChannel | None = None
    ) -> str:
        """Joins a voice channel."""
        assert isinstance(ctx.author, Member)
        assert ctx.guild is not None

        if not channel:
            if not (ctx.author.voice and ctx.author.voice.channel):
                return 'You are not currently in a voice channel, nor did you provide a voice channel to join.'

            channel = ctx.author.voice.channel

        player = self.node.get_player(ctx.guild)

        await player.connect(channel)

        return f'Joined {channel.mention}'

    @command()
    async def play(self, ctx: BoboContext, *, query: str) -> str:
        assert ctx.guild is not None

        player = self.node.get_player(ctx.guild)

        if not player.is_connected():
            await self.join(ctx)

        track = await self.node.get_track(
            query, source=Source.youtube, prefer_selected_track=False
        )

        if isinstance(track, Playlist):
            actual_tracks = track.tracks

            return f'Playing playlist: `{track.name}` with {len(actual_tracks)} tracks.'

        ...

        return f'Playing track: `{track.title}`.'

    @command(aliases=['disconnect'])
    async def leave(self, ctx: BoboContext) -> str:
        """Leaves the current voice channel."""
        assert ctx.guild is not None

        player = self.node.get_player(ctx.guild)

        if not player.is_connected():
            return 'I am not currently connected to a voice channel.'

        channel = player.channel

        await player.disconnect()

        return f'Left {channel.mention}'


setup = Music.setup
