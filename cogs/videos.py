from __future__ import annotations

from typing import TYPE_CHECKING, Tuple
from io import BytesIO

import discord
import pytube


from core import Cog, command, BaseView, async_executor

if TYPE_CHECKING:
    from discord import Interaction

    from core import BoboContext

class YouTube:
    __slots__ = ('_yt',)

    def __init__(self, url: str) -> None:
        self._yt = pytube.YouTube(url)

    @async_executor
    def check_availablity(self) -> bool:
        try:
            self._yt.check_availability()
        except pytube.exceptions.VideoUnavailable:
            return False
    
    @async_executor
    def get_best_video(self, max_file_size: int) -> Tuple[BytesIO, str] | None:
        ordered = self._yt.streams.filter(progressive=True).order_by('resolution').desc()
        
        filtered = filter(lambda x: x.filesize <= max_file_size, ordered)

        b = BytesIO()
        try:
            stream = list(filtered)[0]
        except IndexError:
            return None

        stream.stream_to_buffer(b)
        b.seek(0)

        return b, stream.subtype
    
    @async_executor
    def get_best_audio(self, max_file_size: int) -> Tuple[BytesIO, str] | None:
        ordered = self._yt.streams.filter(only_audio=True, subtype='mp4').order_by('abr').desc()

        filtered = filter(lambda x: x.filesize <= max_file_size, ordered)

        b = BytesIO()
        try:
            stream = list(filtered)[0]
        except IndexError:
            return None

        stream.stream_to_buffer(b)
        b.seek(0)

        return b, stream.subtype

class VideoPrompt(BaseView):
    @discord.ui.button(label='Video', style=discord.ButtonStyle.primary)
    async def video(self, _, interaction: Interaction) -> None:
        self.result = 'video'

        await interaction.response.send_message('Downloading video, please wait.')
        await self.disable_all(interaction)
        
        self.stop()
    
    @discord.ui.button(label='Audio', style=discord.ButtonStyle.primary)
    async def audio(self, _, interaction: Interaction) -> None:
        self.result = 'audio'

        await interaction.response.send_message('Downloading audio, please wait.')
        await self.disable_all(interaction)
        
        self.stop()
    
    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.red)
    async def cancel(self, _, interaction: Interaction) -> None:
        await interaction.response.send_message('Cancelling')
        
        self.stop()

class Videos(Cog):
    @command()
    async def yt(self, ctx: BoboContext, *, url: str):
        tube = YouTube(url)

        if not tube.check_availablity():
            return 'Video not available for download.'
        
        prompt = VideoPrompt(user_id=ctx.author.id)

        embed = ctx.embed(title=tube._yt.title, url=url)
        
        embed.set_thumbnail(url=tube._yt.thumbnail_url)
        embed.set_author(name=tube._yt.author, url=tube._yt.channel_url)

        await ctx.send(embed=embed, view=prompt)

        if await prompt.wait():
            return
        
        filesize_limit = 0

        if ctx.guild:
            filesize_limit = ctx.guild.filesize_limit
        else:
            filesize_limit = 8388608

        if prompt.result == 'video':
            b, file_type = await tube.get_best_video(filesize_limit)
        else:
            b, file_type = await tube.get_best_audio(filesize_limit)
        
        return discord.File(b, filename=f'bobo-bot-youtube-download.{file_type}')

setup = Videos.setup
