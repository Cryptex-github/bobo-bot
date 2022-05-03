from __future__ import annotations

from typing import TYPE_CHECKING, Final
from io import BytesIO

from aiohttp import ClientTimeout

from discord import Color, StickerFormatType, DeletedReferencedMessage, File, utils
from core.utils import async_executor
from webcolors import name_to_rgb, rgb_to_name

from discord.ext.commands import (
    PartialEmojiConverter,
    PartialEmojiConversionFailure,
    UserConverter,
    UserNotFound,
    Converter,
    ColorConverter as _ColorConverter,
    BadColorArgument,
    BadArgument,
    param
)
from PIL import Image, ImageColor

from core import Cog, Regexs
from core.command import command
from core.context import BoboContext

utils.is_inside_class = (
    lambda _: True
)  # Hacky but is necessary for auto commands to work

RGB_SCALE: Final[int] = 255
CMYK_SCALE: Final[int] = 100


if TYPE_CHECKING:
    from discord import Message, User, Member, Embed


class ColorConverter(Converter[tuple[int, int, int]]):
    async def convert(self, ctx: BoboContext, argument: str) -> tuple[int, int, int]:
        try:
            color = await _ColorConverter().convert(ctx, argument)
            color = color.to_rgb()
        except BadColorArgument:
            if argument.isdigit() and int(argument) <= 16777215:
                try:
                    arg = int(argument)
                    red = (arg >> 16) & 255
                    green = (arg >> 8) & 255
                    blue = arg & 255

                    return red, green, blue
                except ValueError:
                    pass
            
            try:
                color = name_to_rgb(argument)
            except ValueError:
                try:
                    color = ImageColor.getrgb(argument)
                except ValueError:
                    raise BadArgument('Unable to parse color given.')

        return tuple(int(c) for c in color)


class ImageResolver:
    __slots__ = ('ctx', 'static')

    def __init__(self, ctx: BoboContext, static: bool) -> None:
        self.ctx = ctx
        self.static = static

    async def check_attachments(self, message: Message) -> str | None:
        if embeds := message.embeds:
            for embed in embeds:
                if embed.type == 'image':
                    return embed.thumbnail.url
                elif embed.type == 'rich':
                    if url := embed.image.url:
                        return url
                    if url := embed.thumbnail.url:
                        return url
                elif embed.type == 'article':
                    if url := embed.thumbnail.url:
                        return url

        if attachments := message.attachments:
            for attachment in attachments:
                if attachment.height:
                    if attachment.filename.endswith('.gif') and self.static:
                        return None

                    return attachment.url

        if stickers := message.stickers:
            for sticker in stickers:
                if sticker.format is not StickerFormatType.lottie:
                    if sticker.format is StickerFormatType.apng and not self.static:
                        return sticker.url

        if message.content:
            if url := await self.parse_content(message.content):
                return url

        return None

    def to_avatar(self, author: User | Member) -> str:
        if self.static:
            return author.display_avatar.with_format('png').url

        return author.display_avatar.with_static_format('png').url

    async def parse_content(self, content: str) -> str | None:
        ctx = self.ctx
        static = self.static

        try:
            emoji = await PartialEmojiConverter().convert(ctx, content)

            if emoji.is_custom_emoji():
                if emoji.animated and not static:
                    return emoji.url

                return emoji.url.replace('.gif', '.png')

            try:
                return f'https://twemoji.maxcdn.com/v/latest/72x72/{ord(content):x}.png'
            except TypeError:
                pass
        except PartialEmojiConversionFailure:
            pass

        try:
            user = await UserConverter().convert(ctx, content)

            return self.to_avatar(user)
        except UserNotFound:
            pass

        content = content.strip('<>')

        if Regexs.URL_REGEX.match(content):
            return content

        return None

    async def get_image(self, arg: str | None = None) -> str:
        if ref := self.ctx.message.reference:
            message = ref.resolved

            if isinstance(message, DeletedReferencedMessage) and ref.message_id:
                message = await self.ctx.channel.fetch_message(ref.message_id)

            if message and not isinstance(message, DeletedReferencedMessage):
                if res := await self.check_attachments(message):
                    return res

        if res := await self.check_attachments(self.ctx.message):
            return res

        if not arg:
            return self.to_avatar(self.ctx.author)

        if res := await self.parse_content(arg):
            return res

        return self.to_avatar(self.ctx.author)


class Images(Cog):
    async def cog_load(self) -> None:
        endpoint_list = ['invert', 'flip', 'mirror', 'floor', 'roo', 'reverse']

        for endpoint in endpoint_list:
            async with self.bot.session.get(
                f'http://127.0.0.1:8085/images/{endpoint}'
            ) as resp:
                description = (await resp.json())['doc']

            @command(name=endpoint, description=description)
            async def image_endpoint_command(
                self, ctx, target: str | None = None
            ) -> str | File | tuple[str, File]:
                async with ctx.typing():
                    resolver = ImageResolver(ctx, False)

                    url = await resolver.get_image(target)

                    async with self.bot.session.post(
                        f'http://127.0.0.1:8085/images/{ctx.command.qualified_name}',
                        json={'url': url},
                        timeout=ClientTimeout(total=600),
                    ) as resp:
                        if resp.status == 200:
                            if resp.headers['Content-Type'] == 'image/gif':
                                fmt = 'gif'
                            else:
                                fmt = 'png'

                            return (
                                f'Process Time: {round(float(resp.headers["Process-Time"]) * 1000, 3)}ms',
                                File(
                                    BytesIO(await resp.read()),
                                    f'bobo_bot_{ctx.command.qualified_name}.{fmt}',
                                ),
                            )

                        if resp.status == 400:
                            return (await resp.json())['message']

                        return await resp.text()

            self.__cog_commands__ += (image_endpoint_command,)

    @staticmethod
    @async_executor
    def _create_color_image(rgb: tuple[int, int, int]) -> BytesIO:
        with Image.new('RGB', (200, 200), rgb) as image:
            fp = BytesIO()
            image.save(fp, 'PNG')
            fp.seek(0)

            return fp

    @staticmethod
    def _rgb_to_hsv(_r: int, _g: int, _b: int) -> tuple[float, float, float]:
        r, g, b = _r / 255.0, _g / 255.0, _b / 255.0

        mx = max(r, g, b)
        mn = min(r, g, b)
        df = mx - mn

        if mx == r:
            h = (60 * ((g - b) / df) + 360) % 360
        elif mx == g:
            h = (60 * ((b - r) / df) + 120) % 360
        elif mx == b:
            h = (60 * ((r - g) / df) + 240) % 360
        else:
            h = 0

        s = 0 if mx == 0 else (df / mx) * 100
        v = mx * 100

        return h, s, v

    @staticmethod
    def _rgb_to_xy_bri(_r: int, _g: int, _b: int) -> tuple[float, float, float]:
        r, g, b = _r / 255.0, _g / 255.0, _b / 255.0

        xyb = (
            (0.412453 * r + 0.35758 * g + 0.180423 * b),
            (0.212671 * r + 0.71516 * g + 0.072169 * b),
            (0.019334 * r + 0.119193 * g + 0.950227 * b),
        )

        return tuple((round(i * 100) for i in xyb))

    @staticmethod
    def _rgb_to_hsl(_r: int, _g: int, _b: int) -> str:
        r, g, b = _r / 255.0, _g / 255.0, _b / 255.0

        mx = max(r, g, b)
        mn = min(r, g, b)
        df = mx - mn

        if mx == r:
            h = (60 * ((g - b) / df) + 360) % 360
        elif mx == g:
            h = (60 * ((b - r) / df) + 120) % 360
        elif mx == b:
            h = (60 * ((r - g) / df) + 240) % 360
        else:
            h = 0

        s = 0 if mx == 0 else (df / mx) * 100
        lightness = ((mx + mn) / 2) * 100

        return f'({round(h)}, {round(s)}%, {round(lightness)}%)'

    @staticmethod
    def _rgb_to_cmyk(r: int, g: int, b: int) -> tuple[int | float, int | float, int | float, int | float]:
        if (r, g, b) == (0, 0, 0):
            return 0, 0, 0, CMYK_SCALE

        c = 1 - r / RGB_SCALE
        m = 1 - g / RGB_SCALE
        y = 1 - b / RGB_SCALE

        min_cmy = min(c, m, y)

        c = (c - min_cmy) / (1 - min_cmy)
        m = (m - min_cmy) / (1 - min_cmy)
        y = (y - min_cmy) / (1 - min_cmy)
        k = min_cmy

        return tuple((round(i) for i in (c * CMYK_SCALE, m * CMYK_SCALE, y * CMYK_SCALE, k * CMYK_SCALE)))

    @command()
    async def color(self, ctx: BoboContext, *, color: tuple[int, int, int] = param(converter=ColorConverter)) -> tuple[Embed, File]:
        try:
            name = rgb_to_name(color)
        except ValueError:
            name = None
        
        embed = ctx.embed(color=Color.from_rgb(*color))

        if name:
            embed.title = name
        
        embed.add_field(name='RGB', value=str(color))
        embed.add_field(name='CMYK', value=str(self._rgb_to_cmyk(*color)))

        hex_ = '%02x%02x%02x' % color
        embed.add_field(name='HEX', value=f'#{hex_} | 0x{hex_}')

        embed.add_field(name='HSL', value=self._rgb_to_hsl(*color))
        embed.add_field(name='XYZ', value=str(self._rgb_to_xy_bri(*color)))

        embed.set_thumbnail(url=f'attachment://color_{hex_}.png')

        return embed, File(await self._create_color_image(color), f'color_{hex_}.png')



setup = Images.setup
