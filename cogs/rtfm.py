from __future__ import annotations

import os
from urllib.parse import quote
import zlib
from asyncio import to_thread
from io import BytesIO
from typing import Iterator, NamedTuple

import discord
from discord.ext.menus import ListPageSource
from discord.ext.menus.views import ViewMenuPages

from core import Cog, Regexes, RTFMCacheManager, finder
from core.command import group
from core.types import PossibleRTFMSources


class RustDocParsedResult(NamedTuple):
    title: str
    signature: str
    description: str


class RTFMMenuSource(ListPageSource):
    def __init__(self, data: list[tuple[str, str]], name: str) -> None:
        self.name = name

        super().__init__(data, per_page=10)

    async def format_page(self, menu, entries) -> dict[str, discord.Embed]:
        return {
            'embed': menu.ctx.embed(
                title=self.name,
                description='\n'.join(f'[{key}]({url})' for key, url in entries),
            )
            .set_author(
                name=str(menu.ctx.author), icon_url=str(menu.ctx.author.display_avatar)
            )
            .set_footer(
                text=f'Page {menu.current_page + 1}/{self.get_max_pages()} Total Entries: {len(self.entries)}'
            )
        }


class RTFM(Cog):
    async def cog_load(self):
        self.cache = RTFMCacheManager(self.bot.redis)

    @staticmethod
    def parse_sphinx_object_inv(stream: BytesIO, base_url: str) -> dict[str, str]:
        """
        Parses Sphinx object inventory file.
        """
        data = {}

        sphinx_version = stream.readline().rstrip()[2:]  # To strip \n

        if sphinx_version != b'Sphinx inventory version 2':
            raise RuntimeError(f'Unsupported Sphinx version: {sphinx_version.decode()}')

        stream.readline()
        stream.readline()

        if b'zlib' not in stream.readline():
            raise RuntimeError('Unsupported compression method')

        decompressor = zlib.decompressobj()

        def yield_decompressed_bytes(data: BytesIO) -> Iterator[str]:
            while True:
                chunk = data.read(16 * 1024)
                if not chunk:
                    break

                decompressed_line = decompressor.decompress(chunk)

                yield decompressed_line.decode('utf-8')

        _data = ''.join(yield_decompressed_bytes(stream))

        for line in _data.split('\n'):
            match = Regexes.SPHINX_ENTRY_REGEX.match(line)

            if not match:
                continue

            name, directive, _, location, display = match.groups()

            domain, _, subdirective = directive.partition(':')

            if directive == 'std:doc':
                subdirective = 'label'

            if location.endswith('$'):
                location = location[:-1] + name

            key = name if display == '-' else display
            prefix = f'{subdirective}:' if domain == 'std' else ''

            data[f'{prefix}{key}'] = os.path.join(base_url, location)

        return data

    async def sphinx_rtfm(
        self, ctx, source: PossibleRTFMSources, query: str | None
    ) -> None:
        source_to_url_map = {
            'python': 'https://docs.python.org/3/',
            'asyncpg': 'https://magicstack.github.io/asyncpg/current/',
            'discordpy': 'https://discordpy.readthedocs.io/en/latest/',
            'discordpy_master': 'https://discordpy.readthedocs.io/en/master/',
        }

        url = source_to_url_map[source]

        if not query:
            await ctx.send(url)

            return

        if results := await self.cache.get(source, ''):
            ...
        else:

            async with self.bot.session.get(url + 'objects.inv') as resp:
                results = await to_thread(
                    self.parse_sphinx_object_inv, BytesIO(await resp.read()), url
                )

            await self.cache.add(
                source, '', results
            )  # Set query to '' because we are caching the entire object

        # matches = self.fuzzy_finder(query, results)
        matches = finder(query, list(results.items()), key=lambda x: x[0], lazy=False)

        if not matches:
            await ctx.send(f'No results found for your query.')

            return

        pages = ViewMenuPages(source=RTFMMenuSource(matches, source))  # type: ignore

        await pages.start(ctx)

    @group()
    async def rtfm(self, ctx) -> None:
        """
        Query documentations.
        """
        await ctx.send_help(ctx.command)

    @rtfm.command(aliases=['py', 'python3'])
    async def python(self, ctx, *, query: str | None = None) -> None:
        """
        Search Python 3 documentation.
        """
        await self.sphinx_rtfm(ctx, 'python', query)

    @rtfm.command(aliases=['pg', 'postgresql'])
    async def asyncpg(self, ctx, *, query: str | None = None) -> None:
        """
        Search asyncpg documentation.
        """
        await self.sphinx_rtfm(ctx, 'asyncpg', query)

    @rtfm.command(aliases=['dpy', 'discordpy_latest'])
    async def discordpy(self, ctx, *, query: str | None = None) -> None:
        """
        Search discordpy documentation.
        """
        await self.sphinx_rtfm(ctx, 'discordpy', query)

    @rtfm.command(aliases=['dpy_master'])
    async def discordpy_master(self, ctx, *, query: str | None = None) -> None:
        """
        Search discordpy master branch documentation.
        """
        await self.sphinx_rtfm(ctx, 'discordpy_master', query)

    async def parse_rust_doc(
        self, url: str, *, query: str, crate: str | None = None
    ) -> list[tuple[str, str]] | None:
        resp = await self.bot.html_session.get(
            f'{url}/{crate if crate else "std"}/?search={query}'
        )
        await resp.html.arender()

        try:
            a = resp.html.find('.search-results')[0].find('a')
        except IndexError:
            return

        results = {}

        for element in a:
            try:
                div = element.find('.result-name')[0]
            except IndexError:
                div = element

            key = ''.join(e.text for e in div.find('span')).replace(':', r'\:')

            results[key] = url + element.attrs['href'].replace('..', '')

        if crate:
            await self.cache.add('crates', f'{crate}:{query}', results)
        else:
            await self.cache.add('rust', query, results)

        return list(results.items())

    async def parse_rust_struct(self, url: str) -> RustDocParsedResult:
        resp = await self.bot.html_session.get(url)
        await resp.html.arender()

        title = resp.html.find('.fqn')[0].full_text
        signature = resp.html.find('code')[0].text
        description = resp.html.find('p')[0].full_text

        return RustDocParsedResult(title, signature, description)

    @rtfm.command()
    async def rust(self, ctx, *, query: str | None = None) -> str | None:
        """
        Search Rust standard library documentation.
        """
        base_url = 'https://doc.rust-lang.org'

        if not query:
            return base_url + '/std'

        query = quote(query.lower())

        if cached := await self.cache.get('rust', query):
            pages = ViewMenuPages(
                source=RTFMMenuSource(list(cached.items()), 'Rust Standard Library')
            )

            await pages.start(ctx)

            return

        res = await self.parse_rust_doc(base_url, query=query)

        if not res:
            return 'No results found for your query.'

        pages = ViewMenuPages(source=RTFMMenuSource(res, 'Rust Standard Library'))

        await pages.start(ctx)

    @rtfm.command(aliases=['crate'])
    async def crates(self, ctx, crate: str, *, query: str | None = None) -> str | None:
        """
        Search a crate's documentation.
        """
        base_url = 'https://docs.rs'
        if not query:
            crate_url = base_url + '/' + crate

            async with self.bot.session.get(crate_url) as resp:
                if resp.status != 200:
                    return 'Crate not found.'

            return crate_url

        query = quote(query.lower())

        if cached := await self.cache.get('crates', f'{crate}:{query}'):
            pages = ViewMenuPages(source=RTFMMenuSource(list(cached.items()), crate))

            await pages.start(ctx)

            return

        res = await self.parse_rust_doc(base_url, query=query, crate=crate)

        if not res:
            return 'No results found for your query.'

        pages = ViewMenuPages(source=RTFMMenuSource(res, crate))

        await pages.start(ctx)


setup = RTFM.setup
