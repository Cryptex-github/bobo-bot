from __future__ import annotations

from typing import TYPE_CHECKING, TypeAlias, Type, cast

import magmatic
from magmatic import Source, Playlist, Track as _Track, Player as _Player, Node as _Node, Queue as _Queue, LoopType

from discord import VoiceChannel, StageChannel, Member, Embed, ButtonStyle
from discord.ui import button, Modal, TextInput, Select
from discord.utils import MISSING, utcnow

from config import LavalinkConnectionDetails

from core import Cog, command
from core.view import BaseView
from core.paginator import EmbedListPageSource, ViewMenuPages

if TYPE_CHECKING:
    from discord import Embed, Message
    from discord import Interaction
    from discord.ui import Button
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


class SetVolumeModal(Modal, title='Set Volume'):
    volume = TextInput(label='Volume', min_length=1, max_length=3)

    async def on_submit(self, interaction: Interaction) -> None:
        await interaction.response.send_message(f'Setted Volume to {self.volume}%')

        self.stop()


class LoopTypeSelect(Select):
    def __init__(self) -> None:
        super().__init__()

        self.add_option(label='None', value='None')
        self.add_option(label='Track', value='Track', emoji='🔂')
        self.add_option(label='Queue', value='Queue', emoji='🔁')
    
    async def callback(self, interaction: Interaction) -> None:
        await interaction.response.send_message(f'Setted loop type to {self.values[0]}', ephemeral=True)
        
        if self.view:
            self.view.stop()


class MusicController(BaseView):
    def __init__(self, player: Player, user_id: int, timeout: int = 180) -> None:
        super().__init__(user_id, timeout)

        self.player = player
    
    def make_embed(self) -> Embed:
        embed = self.player.ctx.embed()
        guild = self.player.bot.get_guild(self.player.guild_id)

        assert guild is not None

        embed.set_author(name='Music Controller: ' + guild.name, icon_url=guild.icon.url if guild.icon else None)

        embed.add_field(name='Volume', value=str(self.player.volume) + '%')
        embed.add_field(name='Loop Type', value=self.player.queue.loop_type.name)
        embed.add_field(name='Is paused', value=str(self.player.is_paused()))
        
        embed.timestamp = utcnow()

        return embed
    
    @button(label='Volume', emoji='🔊', style=ButtonStyle.primary)
    async def set_volume(self, interaction: Interaction, button: Button) -> None:
        modal = SetVolumeModal()

        await interaction.response.send_modal(modal)
        await modal.wait()

        try:
            volume = int(modal.volume) # type: ignore
        except ValueError:
            return

        await self.player.set_volume(volume)
    
    @button(label='Loop Type', emoji='🔁', style=ButtonStyle.primary)
    async def set_loop_type(self, interaction: Interaction, button: Button) -> None:
        view = BaseView(interaction.user.id)

        select = LoopTypeSelect()
        view.add_item(select)

        await interaction.response.send_message(view=view, ephemeral=True)
        await view.wait()

        selected = select.values[0]
        
        if selected == 'None':
            loop_type = LoopType.none
        elif selected == 'Track':
            loop_type = LoopType.track
        else:
            loop_type = LoopType.queue
        
        self.player.loop_type = loop_type
    
    @button(label='Toggle Pause', emoji='⏸', style=ButtonStyle.primary)
    async def toggle_pause(self, interaction: Interaction, button: Button) -> None:
        await self.player.toggle_pause()

        await interaction.response.send_message(f'Toggled pause to {self.player.is_paused}', ephemeral=True)


class MusicControllerInvoke(BaseView):
    def __init__(self, player: Player, user_id: int, timeout: int = 180) -> None:
        super().__init__(user_id, timeout)
        self.player = player

    @button(label='Music Controller', emoji='🎵', style=ButtonStyle.primary)
    async def invoke(self, interaction: Interaction, button: Button) -> None:
        controller = MusicController(self.player, interaction.user.id)

        await interaction.response.send_message(view=controller, embed=controller.make_embed(), ephemeral=True)


class Player(_Player['BoboBot']):
    if TYPE_CHECKING:
        ctx: BoboContext
        loop_type: LoopType

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

        self._prev_message: Message | None = None
        self.queue = Queue()

    async def do_next(self) -> None:
        track = self.queue.get()

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
            hours, remainder = divmod(int(self.position or 0), 3600)
            minutes, seconds = divmod(remainder, 60)
            position = f'{hours:02d}:{minutes:02d}:{seconds:02d}'
        except:
            position = 'Position too long.'

        try:
            percentage = 100 / (track.duration or 0) * (self.position or 0)

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
                f'**{track.title}**'
                f'\n{bar}\n\n{position}/{duration}'
            ),
            url=track.uri,
        )

        embed.add_field(name='Author', value=track.author)
        embed.add_field(
            name='Requested By', value=track.metadata.requestor.mention
        )
        embed.add_field(name='Volume', value=f'{self.volume}%')

        if track.thumbnail:
            embed.set_thumbnail(url=track.thumbnail)

        return embed

    async def send_embed(self) -> None:
        if track := self.queue.current:
            if message := self._prev_message:
                await message.delete()
            
            view = MusicControllerInvoke(self, self.ctx.author.id)

            self._prev_message = await self.ctx.send(embed=self._make_embed(track), view=view)


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
            self.bot.magmatic_node = Node(
                bot=self.bot,
                host=LavalinkConnectionDetails.host,
                port=LavalinkConnectionDetails.port,
                password=LavalinkConnectionDetails.password,
                resume=False,
                identifier='BoboBot Lavalink Node',
                session=self.bot.session,
            )

            await self.bot.magmatic_node.start()
            magmatic.add_node(self.bot.magmatic_node)

        node = cast(Node, self.bot.magmatic_node)
        self.node = node

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
    async def queue(self, ctx: BoboContext) -> str | None:
        """Shows the current queue."""
        assert ctx.guild is not None

        player = self.node.get_player(ctx.guild)

        if player.queue.is_empty():
            return 'The queue is empty.'

        pages = EmbedListPageSource(
            [
                f'{i}: [**{track.title}**]({track.uri})\nRequested By: {track.metadata.requestor.mention}'
                for i, track in enumerate(player.queue.queue, 1)
            ],
            title='Current Queue',
        )

        pages = ViewMenuPages(pages)
        await pages.start(ctx)

    @command()
    async def pause(self, ctx: BoboContext) -> str:
        """Pauses the currently playing track."""
        assert ctx.guild is not None

        player = self.node.get_player(ctx.guild)

        if not player.is_playing():
            return 'No track is currently playing.'

        await player.pause()

        return '\U0001f44d'

    @command(aliases=['resume'])
    async def unpause(self, ctx: BoboContext) -> str:
        """Resumes the currently paused track."""
        assert ctx.guild is not None

        player = self.node.get_player(ctx.guild)

        if not player.is_paused():
            return 'No track is currently paused.'

        await player.resume()

        return '\U0001f44d'

    @command()
    async def skip(self, ctx: BoboContext) -> str:
        """Skips the currently playing track."""
        assert ctx.guild is not None

        player = self.node.get_player(ctx.guild)

        if not player.is_playing():
            return 'No track is currently playing.'

        await player.stop()

        return '\U0001f44d'

    @command()
    async def play(self, ctx: BoboContext, *, query: str) -> str:
        """Plays a track."""
        assert ctx.guild is not None
        assert isinstance(ctx.author, Member)

        if not (ctx.author.voice and ctx.author.voice.channel):
            return 'You are not currently in a voice channel.'

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
                if track_ := player.queue.get():
                    await player.play(track_)

            return f'Added playlist: `{track.name}` with {len(actual_tracks)} tracks.'

        track.metadata = MetaData(ctx.author)

        track = cast(Track, track)

        player.queue.add(track)

        if not player.is_playing():
            if track_ := player.queue.get():
                await player.play(track_)

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
