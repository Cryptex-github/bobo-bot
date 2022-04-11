from __future__ import annotations

from typing import TYPE_CHECKING

from asyncpg.exceptions import UniqueViolationError, UndefinedColumnError
from discord.ext import commands
from discord.utils import escape_mentions

from core import BoboContext, Cog

if TYPE_CHECKING:
    from asyncpg.pool import Pool

from core import BoboContext, Cog, command

class TagManager:
    def __init__(self, db: Pool):
        self.db = db
    
    async def new_tag(self, ctx: BoboContext, name: str, content: str):
        await self.db.execute(
            'INSERT INTO tags (name, content, author_id, message_id) VALUES ($1, $2, $3)',
            name, content, ctx.author.id, ctx.message.id
        )
    
    async def get_tag_content(self, name: str) -> str | None:
        return await self.db.fetchval(
            'SELECT content FROM tags WHERE name = $1', name
        )


class Tag(Cog):
    async def cog_load(self):
        self.tag_manager = TagManager(self.bot.db)
    
    @command()
    async def tag(self, ctx: BoboContext, name: str):
        content = await self.tag_manager.get_tag_content(name)
        if not content:
            await ctx.send('Tag not found.')

            return
        
        await ctx.send(escape_mentions(content))
    
    @tag.command(aliases=['create'])
    async def new(self, ctx: BoboContext, name: str, *, content: str) -> None:
        """Creates a new tag."""
        if len(name) > 200:
            await ctx.send('Tag name is too long.')

            return

        try:
            await self.tag_manager.new_tag(ctx, name, content)
        except UniqueViolationError:
            await ctx.send('Tag already exists.')

            return

        await ctx.send('Tag created.')
    
    @tag.command(aliases=['delete'])
    async def remove(self, ctx: BoboContext, name: str) -> None:
        """
        Deletes a tag.
        """
        if not await self.tag_manager.remove_tag(ctx, name):
            await ctx.send('Tag not found, are you sure you owns it?')

            return
        
        return content
