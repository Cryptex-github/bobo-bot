from __future__ import annotations

from asyncio.subprocess import create_subprocess_exec, PIPE, DEVNULL
from typing import TYPE_CHECKING, NamedTuple
from io import BytesIO

import discord


from core import Cog, command, BaseView

if TYPE_CHECKING:
    from discord import Interaction

    from core import BoboContext


class VideoMetadata(NamedTuple):
    title: str
    thumbnail_url: str


class YoutubeDownloader:
    def __init__(self, url: str, *, max_filesize: int, audio_only: bool = False) -> None:
        self.url = url
        self.max_filesize = max_filesize
        self.audio_only = audio_only

    @staticmethod
    async def metadata(url: str) -> VideoMetadata:
        proc = await create_subprocess_exec('yt-dlp', url, '-qse', '--get-id', '--skip-download', stdout=PIPE, stderr=DEVNULL)

        stdout, _ = await proc.communicate()
        stdout = stdout.decode('utf-8')

        if 'ERROR' in stdout:
            raise ValueError('Invalid URL')

        info = stdout.split('\n')
        title = info[0]
        video_id = info[1]

        return VideoMetadata(
            title=title,
            thumbnail_url=f'http://img.youtube.com/vi/{video_id}/maxresdefault.jpg'
        )

    async def download(self) -> tuple[BytesIO, str]:
        args = (
            self.url, 
            '--max-filesize', str(self.max_filesize),
            '-o', '-',
            '--audio-format', 'mp3',
            '--recode-video', 'mp4',
        )

        if self.audio_only:
            args += ('-f', 'bestaudio')
        else:
            args += ('-f', 'bestvideo+bestaudio')

        proc = await create_subprocess_exec('yt-dlp', *args, stdout=PIPE, stderr=DEVNULL)

        stdout, _ = await proc.communicate()

        return BytesIO(stdout), ('mp3' if self.audio_only else 'mp4')


class VideoPrompt(BaseView):
    @discord.ui.button(label='Video', style=discord.ButtonStyle.primary)
    async def video(self, interaction: Interaction, _) -> None:
        self.result = 'video'

        await self.disable_all(interaction)
        await interaction.followup.send('Downloading video, please wait.')

        self.stop()

    @discord.ui.button(label='Audio', style=discord.ButtonStyle.primary)
    async def audio(self, interaction: Interaction, _) -> None:
        self.result = 'audio'

        await self.disable_all(interaction)
        await interaction.followup.send('Downloading audio, please wait.')

        self.stop()

    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.red)
    async def cancel(self, interaction: Interaction, _) -> None:
        await interaction.response.send_message('Cancelling')

        self.stop()


class Videos(Cog):
    @command()
    async def yt(self, ctx: BoboContext, *, url: str) -> str | discord.File:
        await ctx.trigger_typing()

        try:
            metadata = await YoutubeDownloader.metadata(url)
        except ValueError:
            return 'Video not available for download.'

        prompt = VideoPrompt(user_id=ctx.author.id)

        embed = ctx.embed(title=metadata.title, url=url)

        embed.set_thumbnail(url=metadata.thumbnail_url)

        await ctx.send(embed=embed, view=prompt)

        if await prompt.wait():
            return 'Timed out'

        filesize_limit = 0

        if ctx.guild:
            filesize_limit = ctx.guild.filesize_limit
        else:
            filesize_limit = 8388608

        yt = YoutubeDownloader(url, max_filesize=filesize_limit, audio_only=prompt.result == 'audio')

        async with ctx.typing():
            b, file_type = await yt.download()

        return discord.File(b, filename=f'bobo-bot-youtube-download.{file_type}')


setup = Videos.setup
