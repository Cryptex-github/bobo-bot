from __future__ import annotations

from typing import TYPE_CHECKING, TypeAlias

import magmatic
from magmatic import Source, Playlist, Track as _Track, Player

from discord import VoiceChannel, StageChannel, Member

from config import LavalinkConnectionDetails

from core import Cog, command

if TYPE_CHECKING:
    from discord import Embed

    from core.context import BoboContext

class MetaData:
    __slots__ = ('requestor',)

    def __init__(self, requestor: Member) -> None:
        self.requestor = requestor


Track: TypeAlias = _Track[MetaData]

class Queue:
    __slots__ = ('_queue', '_current', '_position', 'loop', '_ctx')

    def __init__(self, ctx: BoboContext) -> None:
        self._queue: list[Track] = []
        self._position: int = 0
        self.loop: bool = False

        self._ctx: BoboContext = ctx

    @classmethod
    def with_tracks(cls, ctx: BoboContext, tracks: list[Track]) -> Queue:
        queue = cls(ctx)
        queue.append_tracks(tracks)

        return queue

    def append_track(self, track: Track) -> None:
        self._queue.append(track)

    def append_tracks(self, track: list[Track]) -> None:
        self._queue.extend(track)

    def seek_next(self) -> None:
        self._position += 1

        self._cleanup()

    def seek_prev(self) -> None:
        self._position -= 1

        self._cleanup()

    def seek(self, position: int) -> None:
        self._position = position

        self._cleanup()

    def _cleanup(self) -> None:
        self._queue = self._queue[:self._position]
        self._position = 0

    @property
    def current(self) -> Track:
        return self.queue[self.position]

    @property
    def queue(self) -> list[Track]:
        return self._queue

    @property
    def position(self) -> int:
        return self._position

    @property
    def ctx(self) -> BoboContext:
        return self._ctx

    def _make_embed(self, player: Player) -> Embed:
        track = self.current

        try:
            hours, remainder = divmod(track.duration, 3600)
            minutes, seconds = divmod(remainder, 60)

            duration = f'{hours:02d}:{minutes:02d}:{seconds:02d}'
        except:
            duration = 'Duration too long.'

        try:
            hours, remainder = divmod(track.position, 3600)
            minutes, seconds = divmod(remainder, 60)
            position = f'{hours:02d}:{minutes:02d}:{seconds:02d}'
        except:
            position = 'Position too long.'

        try:
            percentage = 100 / track.duration * track.position

            bar = (
                '`'
                + '⬜' * int(20 / 100 * percentage)
                + '⬛' * int(20 - (20 / 100 * percentage))
                + '`'
            )
        except:
            bar = ''

        embed = self.ctx.embed(
            title='Current Track', 
            description=(
            f'**{self.current.title}** By: **{self.current.author}**'
            f'\n{bar}\n\n{position}/{duration}'
            )
        )
        embed.add_field(name='Requested By', value=f'{self.current.metadata.requestor.mention}')

        return embed


    async def send_embed(self, player: Player) -> None:
        await self.ctx.send(embed=self._make_embed(player))


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
        assert isinstance(ctx.author, Member)

        player = self.node.get_player(ctx.guild)

        if not player.is_connected():
            await self.join(ctx)

        track = await self.node.search_track(
            query, source=Source.youtube, prefer_selected_track=False
        )

        if isinstance(track, Playlist):
            actual_tracks = track.tracks

            if queue := getattr(player, 'queue', None):
                queue.append_tracks(actual_tracks)
            else:
                player.queue = Queue.with_tracks(ctx, actual_tracks)

            for track in actual_tracks:
                track.metadata = MetaData(ctx.author)

            await player.play(player.queue.current)            
            await player.queue.send_embed(player)

            return f'Playing playlist: `{track.name}` with {len(actual_tracks)} tracks.'

        track.metadata = MetaData(ctx.author)

        if queue := getattr(player, 'queue', None):
            queue.append_track(track)
        else:
            player.queue = Queue.with_tracks(ctx, [track])

        await player.play(player.queue.current)
        await player.queue.send_embed(player)

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
