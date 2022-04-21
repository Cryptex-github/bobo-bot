from __future__ import annotations

from typing import TYPE_CHECKING, TypeAlias, Type, cast

import magmatic
from magmatic import Source, Playlist, Track as _Track, Player as _Player, Node as _Node, Queue as _Queue

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

class Queue(_Queue[MetaData]):
    ...


class Player(_Player['BoboBot']):
    if TYPE_CHECKING:
        ctx: BoboContext

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

        self.queue = Queue()
        self.queue.reset()

    async def do_next(self) -> None:
        track = self.queue.skip()

        if not track:
            return

        await self.play(track)
        await self.send_embed()

    async def on_track_end(self, event: TrackEndEvent) -> None:
        await self.do_next()

    async def on_track_stuck(self, event: TrackStuckEvent) -> None:
        await self.do_next()

    def _make_embed(self, track: Track) -> Embed:
        try:
            hours, remainder = divmod(int(track.duration), 3600)
            minutes, seconds = divmod(remainder, 60)

            duration = f'{hours:02d}:{minutes:02d}:{seconds:02d}'
        except:
            duration = 'Duration too long.'

        try:
            hours, remainder = divmod(int(track.position or 0), 3600)
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
                f'**{track.title}** By: **{track.author}**'
                f'\n{bar}\n\n{position}/{duration}'
            ),
        )
        embed.add_field(
            name='Requested By', value=f'{track.metadata.requestor.mention}'
        )

        return embed

    async def send_embed(self) -> None:
        if track := self.queue.current:
            await self.ctx.send(embed=self._make_embed(track))


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

        if ctx.invoked_with in ('join', 'leave', 'play'):
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

        if player.queue.current:
            await player.send_embed()

            return

        return 'No track is currently playing.'

    @command()
    async def play(self, ctx: BoboContext, *, query: str) -> str:
        """Plays a track."""
        assert ctx.guild is not None
        assert isinstance(ctx.author, Member)

        player = self.node.get_player(ctx.guild)
        player.ctx = ctx

        track = await self.node.search_track(
            query, source=Source.youtube, prefer_selected_track=False
        )

        if not track:
            return 'No track matched your query.'

        if not player.is_connected():
            await self.join(ctx)

        if isinstance(track, Playlist):
            actual_tracks = track.tracks

            player.queue.add_multiple(actual_tracks)

            for track in actual_tracks:
                track.metadata = MetaData(ctx.author)

            if not player.is_playing():
                assert player.queue.current is not None

                await player.play(player.queue.current)

            return f'Added playlist: `{track.name}` with {len(actual_tracks)} tracks.'

        track.metadata = MetaData(ctx.author)

        track = cast(Track, track)

        player.queue.add(track)

        if not player.is_playing():
            assert player.queue.current is not None

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
