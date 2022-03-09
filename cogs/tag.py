from __future__ import annotations

from typing import TYPE_CHECKING

from core import BoboContext, Cog, command

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
    
    @command()
    async def tag(self, ctx: BoboContext, name: str):
        content = await self.tag_manager.get_tag_content(name)
        if not content:
            return 'Tag not found.'
        
        return content

setup = Tag.setup