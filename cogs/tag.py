from __future__ import annotations

from typing import TYPE_CHECKING

from asyncpg.exceptions import UniqueViolationError
from discord.ext import commands
from discord.utils import escape_mentions

from core import BoboContext, Cog, group

if TYPE_CHECKING:
    from asyncpg.pool import Pool


class TagManager:
    def __init__(self, db: Pool):
        self.db = db
    
    async def new_tag(self, ctx: BoboContext, name: str, content: str):
        await self.db.execute(
            'INSERT INTO tags (name, content, author_id, message_id) VALUES ($1, $2, $3, $4)',
            name, content, ctx.author.id, ctx.message.id
        )
    
    async def get_tag_content(self, name: str) -> str | None:
        return await self.db.fetchval(
            'SELECT content FROM tags WHERE name = $1', name
        )
    
    async def remove_tag(self, ctx, name: str) -> bool:
        return (await self.db.execute(
            'DELETE FROM tags WHERE name = $1 AND author_id = $2', name, ctx.author.id
        )) != 'DELETE 0'


class Tag(Cog):
    def init(self):
        self.tag_manager = TagManager(self.bot.db)
    
    @commands.group(invoke_without_command=True)
    async def tag(self, ctx: BoboContext, *, name: str) -> None:
        """Shows the content of a tag."""
        content = await self.tag_manager.get_tag_content(name)
        if not content:
            await ctx.send('Tag not found.')

            return
        
        await ctx.send(escape_mentions(content))
    
    @tag.command(alias=['create'])
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
    
    @tag.command(alias=['delete'])
    async def remove(self, ctx: BoboContext, name: str) -> None:
        """
        Deletes a tag.
        """
        if not await self.tag_manager.remove_tag(ctx, name):
            await ctx.send('Tag not found, are you sure you owns it?')

            return
        
        await ctx.send('Tag deleted.')
    

setup = Tag.setup
