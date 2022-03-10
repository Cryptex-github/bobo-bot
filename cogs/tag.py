from __future__ import annotations

from typing import TYPE_CHECKING

from core import BoboContext, Cog, group

if TYPE_CHECKING:
    from asyncpg.pool import Pool


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
    def init(self):
        self.tag_manager = TagManager(self.bot.db)
    
    @group(invoke_without_command=True)
    async def tag(self, ctx: BoboContext, *, name: str) -> str:
        """Shows the content of a tag."""
        content = await self.tag_manager.get_tag_content(name)
        if not content:
            await ctx.send('Tag not found.')
        
        return content
    
    @tag.command(alias=['create'])
    async def new(self, ctx: BoboContext, name: str, *, content: str) -> str:
        """Creates a new tag."""
        if len(name) > 200:
            return 'Tag name is too long.'

        await self.tag_manager.new_tag(ctx, name, content)
        
        await ctx.send('Tag created.')
    

setup = Tag.setup
