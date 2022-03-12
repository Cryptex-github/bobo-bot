import os
import re
import zlib
from asyncio import to_thread
from io import BytesIO
from typing import Dict, Iterator, List, Tuple

import discord
from discord.ext import commands
from discord.ext.menus import ListPageSource
from discord.ext.menus.views import ViewMenuPages

from core import Cog, Regexs, RTFMCacheManager
from core.types import POSSIBLE_RTFM_SOURCES


class RTFMMenuSource(ListPageSource):
    def __init__(self, data: List[Tuple[str]], name: str) -> None:
        self.name = name

        super().__init__(data, per_page=10)
    
    async def format_page(self, menu, entries) -> Dict[str, discord.Embed]:
        return {
            'embed': menu.ctx.embed(title=self.name, description='\n'.join(f'[{key}]({url})' for key, url in entries))
                .set_author(name=str(menu.ctx.author), icon_url=str(menu.ctx.author.display_avatar))
                .set_footer(
                    text=f'Page {menu.current_page + 1}/{self.get_max_pages()} Total Entries: {len(self.entries)}'
                )
        }


class RTFM(Cog):
    def init(self):
        self.cache = RTFMCacheManager(self.bot.redis)
    
    @staticmethod
    def fuzzy_finder(query: str, collection: Dict[str, str]) -> Dict[str, str]:
        results = []

        comp = '.*?'.join(map(re.escape, query))
        reg = re.compile(comp, flags=re.IGNORECASE)

        for k, v in collection.items():
            if out := reg.search(k):
                results.append(len(out.group(), out.start(), (k, v)))
        
        return [x for _, _, x in sorted(results, key=lambda x: (x[0], x[1], x[2][0]))]

    @staticmethod
    def parse_sphinx_object_inv(stream: BytesIO, base_url: str) -> Dict[str, str]:
        """
        Parses Sphinx object inventory file.
        """
        data = {}

        sphinx_version = stream.readline().rstrip()[2:] # To strip \n

        if sphinx_version != b'Sphinx inventory version 2':
            raise RuntimeError(f'Unsupported Sphinx version: {sphinx_version.decode()}')
        
        _ = stream.readline().rstrip()[2:]
        _ = stream.readline()

        if b'zlib' not in stream.readline():
            raise RuntimeError('Unsupported compression method')
        
        decompressor = zlib.decompressobj()

        def yield_decompressed_bytes(self, data: BytesIO) -> Iterator[str]:
            while True:
                chunk = data.read(16 * 1024)
                if not chunk:
                    break
                
                decompressed_line = decompressor.decompress(chunk)

                yield decompressed_line.decode('utf-8').rstrip()
        
        for line in yield_decompressed_bytes(stream):
            match = Regexs.SPHINX_ENTRY_REGEX.match(line)

            if not match:
                continue

            name, _, _, location, display = match.groups()

            if location.endswith('$'):
                location = location[:-1] + name
            
            key = name if display == '-' else display

            data[key] = os.path.join(base_url, location)
        
        return data
    
    async def sphinx_rtfm(self, ctx, source: POSSIBLE_RTFM_SOURCES, query: str) -> None:
        if results := await self.cache.get(source, ''):
            ...
        else:
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

            async with self.bot.session.get(url) as resp:
                results = await to_thread(self.parse_sphinx_object_inv, BytesIO(await resp.read()), url)

            await self.cache.add(source, '', results) # Set query to '' because we are caching the entire object
        
        matches = self.fuzzy_finder(query, results)

        if not matches:
            await ctx.send(f'No results found for your query.')

            return
        
        pages = ViewMenuPages(source=RTFMMenuSource(list(matches.items), source))

        await pages.start(ctx)
    
    @commands.group(invoke_without_command=True)
    async def rtfm(self, ctx) -> None:
        """
        Query documentations.
        """
        await ctx.send_help(ctx.command)
    
    @rtfm.command(alias=['py', 'python3'])
    async def python(self, ctx, *, query: str = None) -> None:
        """
        Search Python 3 documentation.
        """
        await self.sphinx_rtfm(ctx, 'python', query)

setup = RTFM.setup
