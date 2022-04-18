from __future__ import annotations

from typing import TYPE_CHECKING, TypeAlias, Type, cast

import magmatic
from magmatic import Source, Playlist, Track as _Track, Player as _Player, Node as _Node

from discord import VoiceChannel, StageChannel, Member
from discord.utils import MISSING

from config import LavalinkConnectionDetails

from core import Cog, command

if TYPE_CHECKING:
    from discord import Embed
    from discord.channel import VocalGuildChannel
    from discord.abc import Snowflake

    from magmatic.events import TrackEndEvent, TrackStuckEvent

    from core.context import BoboContext
    from core.bot import BoboBot


class MetaData:
    __slots__ = ('requestor',)

    def __init__(self, requestor: Member) -> None:
        self.requestor = requestor


Track: TypeAlias = _Track[MetaData]


class Player(_Player['BoboBot']):
    def __init__(
        self,
        client: BoboBot = MISSING,
        channel: VocalGuildChannel = MISSING,
        /,
        *,
        node: Node = MISSING,
        guild: Snowflake = MISSING,
    ) -> None:
        super().__init__(client, channel, node=node, guild=guild)

        self.queue = Queue(self)

    async def do_next(self) -> None:
        self.queue.seek_next()

        try:
            track = self.queue.current
        except IndexError:
            return

        await self.play(track)
        await self.queue.send_embed()

    async def on_track_end(self, event: TrackEndEvent) -> None:
        await self.do_next()

    async def on_track_stuck(self, event: TrackStuckEvent) -> None:
        await self.do_next()


class Node(_Node['BoboBot']):
    def get_player(
        self,
        guild: Snowflake,
        *,
        cls: Type[Player] = Player,
        fail_if_not_exists: bool = False,
    ) -> Player:
        return super().get_player(
            guild, cls=Player, fail_if_not_exists=fail_if_not_exists
        )


class Queue:
    if TYPE_CHECKING:
        _ctx: BoboContext

    __slots__ = ('_queue', '_current', '_position', 'loop', '_ctx', '_player')

    def __init__(self, player: Player) -> None:
        self._queue: list[Track] = []
        self._position: int = 0
        self.loop: bool = False

        self._player: Player = player

    @classmethod
    def with_tracks(
        cls, ctx: BoboContext, player: Player, tracks: list[Track]
    ) -> Queue:
        queue = cls(player)
        queue.append_tracks(tracks)

        queue._ctx = ctx

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
        self._queue = self._queue[: self._position]
        self._position = 0

    @property
    def player(self) -> Player:
        return self._player

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

    def _make_embed(self) -> Embed:
        track = self.current

        try:
            hours, remainder = divmod(track.duration, 3600)
            minutes, seconds = divmod(remainder, 60)

            duration = f'{hours:02d}:{minutes:02d}:{seconds:02d}'
        except:
            duration = 'Duration too long.'

        try:
            hours, remainder = divmod(track.position or 0, 3600)
            minutes, seconds = divmod(remainder, 60)
            position = f'{hours:02d}:{minutes:02d}:{seconds:02d}'
        except:
            position = 'Position too long.'

        try:
            percentage = 100 / (track.duration or 0) * (track.position or 0)

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
            ),
        )
        embed.add_field(
            name='Requested By', value=f'{self.current.metadata.requestor.mention}'
        )

        return embed

    async def send_embed(self) -> None:
        await self.ctx.send(embed=self._make_embed())


class Music(Cog):
    async def cog_load(self) -> None:
        if not hasattr(self.bot, 'magmatic_node'):
            self.bot.magmatic_node = self.node = Node(
                bot=self.bot,
                host=LavalinkConnectionDetails.host,
                port=LavalinkConnectionDetails.port,
                password=LavalinkConnectionDetails.password,
                resume=False,
                identifier='BoboBot Lavalink Node',
                session=self.bot.session,
            )

            await self.node.start()
            magmatic.add_node(self.node)

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
    async def now(self, ctx: BoboContext) -> str | None:
        """Shows the currently playing track."""
        assert ctx.guild is not None

        player = self.node.get_player(ctx.guild)

        if not hasattr(player, 'queue'):
            return 'No track is currently playing.'

        await player.queue.send_embed()

    @command()
    async def play(self, ctx: BoboContext, *, query: str) -> str:
        """Plays a track."""
        assert ctx.guild is not None
        assert isinstance(ctx.author, Member)

        player = self.node.get_player(ctx.guild)

        track = await self.node.search_track(
            query, source=Source.youtube, prefer_selected_track=False
        )

        if not track:
            return 'No track matched your query.'

        if not player.is_connected():
            await self.join(ctx)

        if isinstance(track, Playlist):
            actual_tracks = track.tracks

            player.queue.append_tracks(actual_tracks)


            for track in actual_tracks:
                track.metadata = MetaData(ctx.author)

            await player.play(player.queue.current)

            return f'Added playlist: `{track.name}` with {len(actual_tracks)} tracks.'

        track.metadata = MetaData(ctx.author)

        track = cast(Track, track)

        player.queue._ctx = ctx

        player.queue.append_track(track)

        await player.play(player.queue.current)

        return f'Added track: `{track.title}`.'

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
