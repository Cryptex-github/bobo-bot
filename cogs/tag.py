from __future__ import annotations

from typing import TYPE_CHECKING
from abc import ABC

from asyncpg.exceptions import UniqueViolationError, UndefinedColumnError
from discord.utils import escape_mentions
from discord import app_commands
from discord.app_commands import Choice

from core import BoboContext, Cog
from core.command import group

if TYPE_CHECKING:
    from asyncpg.pool import Pool
    from discord import Interaction


class BaseTagManager(ABC):
    def __init__(self, db: Pool):
        self.db = db

    async def new_tag(self, name: str, content: str, author_id: int, message_id: int) -> bool:
        try:
            await self.db.execute(
                'INSERT INTO tags (name, content, author_id, message_id) VALUES ($1, $2, $3, $4)',
                name,
                content,
                author_id,
                message_id,
            )

            return True
        except UniqueViolationError:
            return False

    async def get_tag_content(self, name: str) -> str | None:
        return await self.db.fetchval('SELECT content FROM tags WHERE name = $1', name)

    async def remove_tag(self, name: str, author_id) -> bool:
        return (
            await self.db.execute(
                'DELETE FROM tags WHERE name = $1 AND author_id = $2',
                name,
                author_id,
            )
        ) != 'DELETE 0'

    async def edit_tag(self, name: str, content: str, author_id: int) -> bool:
        try:
            await self.db.execute(
                'UPDATE tags SET content = $1 WHERE name = $2 AND author_id = $3',
                content,
                name,
                author_id,
            )

            return True
        except UndefinedColumnError:
            return False


class ContextBasedTagManager(BaseTagManager):
    async def new_tag(self, ctx: BoboContext, name: str, content: str) -> bool:
        return await super().new_tag(
            name,
            content,
            ctx.author.id,
            ctx.message.id,
        )
    
    async def remove_tag(self, ctx: BoboContext, name: str) -> bool:
        return await super().remove_tag(name, ctx.author.id)
    
    async def edit_tag(self, ctx: BoboContext, name: str, content: str) -> bool:
        return await super().edit_tag(name, content, ctx.author.id)


class SlashBasedTagManager(BaseTagManager):
    async def new_tag(self, interaction: Interaction, name: str, content: str) -> bool:
        return await super().new_tag(
            name,
            content,
            interaction.user.id,
            interaction.message.id if interaction.message else 0,
        )
    
    async def remove_tag(self, interaction: Interaction, name: str) -> bool:
        return await super().remove_tag(name, interaction.user.id)
    
    async def edit_tag(self, interaction: Interaction, name: str, content: str) -> bool:
        return await super().edit_tag(name, content, interaction.user.id)
    
    async def get_similar_tags(self, name: str) -> list[str]:
        return [t['name'] for t in await self.db.fetch('SELECT name FROM tags WHERE name % $1 ORDER BY similarity(name, $1) DESC LIMIT 25', name)]


class Tag(Cog):
    async def cog_load(self):
        self.ctx_tag_manager = ContextBasedTagManager(self.bot.db)
        self.slash_tag_manager = SlashBasedTagManager(self.bot.db)
    
    slash_group = app_commands.Group(name='tag', description='Commands to access and manage tags.', guild_ids=[786359602241470464])

    @group()
    async def tag(self, ctx: BoboContext, *, name: str) -> str:
        """Shows the content of a tag."""
        content = await self.ctx_tag_manager.get_tag_content(name)
        if not content:
            return 'Tag not found.'


        return escape_mentions(content)
    
    @slash_group.command()
    @app_commands.describe(name='The name of the tag.')
    async def show(self, interaction: Interaction, name: str) -> None:
        """Shows the content of a tag."""
        content = await self.slash_tag_manager.get_tag_content(name)
        if not content:
            await interaction.response.send_message('Tag not found.')
            
            return

        await interaction.response.send_message(escape_mentions(content))

    @tag.command(aliases=['create'])
    async def new(self, ctx: BoboContext, name: str, *, content: str) -> str:
        """Creates a new tag."""
        if len(name) > 200:
            return'Tag name is too long.'

        if not await self.ctx_tag_manager.new_tag(ctx, name, content):
            return 'Tag already exists.'

        return 'Tag created.'
    
    @slash_group.command()
    @app_commands.describe(name='The name of the tag.', content='The content of the tag.')
    async def create(self, interaction: Interaction, name: str, content: str) -> None:
        """Creates a new tag."""
        if len(name) > 200:
            await interaction.response.send_message('Tag name is too long.')
            
            return

        if not await self.slash_tag_manager.new_tag(interaction, name, content):
            await interaction.response.send_message('Tag already exists.')
            
            return

        await interaction.response.send_message('Tag created.')

    @tag.command(aliases=['delete'])
    async def remove(self, ctx: BoboContext, name: str) -> None:
        """
        Deletes a tag.
        """
        if not await self.ctx_tag_manager.remove_tag(ctx, name):
            await ctx.send('Tag not found, are you sure you owns it?')

            return

        await ctx.send('Tag deleted.')
    
    @slash_group.command(name='remove')
    @app_commands.describe(name='The name of the tag.')
    async def slash_remove(self, interaction: Interaction, name: str) -> None:
        """
        Deletes a tag.
        """
        if not await self.slash_tag_manager.remove_tag(interaction, name):
            await interaction.response.send_message('Tag not found, are you sure you owns it?')
            
            return

        await interaction.response.send_message('Tag deleted.')

    @tag.command()
    async def edit(self, ctx: BoboContext, name: str, *, content: str) -> str:
        """
        Edits a tag.
        """
        if not await self.ctx_tag_manager.edit_tag(ctx, name, content):
            return 'Tag not found, are you sure you owns it?'

        return 'Tag edited.'
    
    @slash_group.command(name='edit')
    @app_commands.describe(name='The name of the tag.', content='The content of the tag.')
    async def slash_edit(self, interaction: Interaction, name: str, content: str) -> None:
        """
        Edits a tag.
        """
        if not await self.slash_tag_manager.edit_tag(interaction, name, content):
            await interaction.response.send_message('Tag not found, are you sure you owns it?')
            
            return

        await interaction.response.send_message('Tag edited.')
    
    @show.autocomplete('name')
    @slash_remove.autocomplete('name')
    @slash_edit.autocomplete('name')
    async def show_autocomplete(self, interaction: Interaction, current: str) -> list[Choice[str]]:
        return [Choice(name=t, value=t) for t in await self.slash_tag_manager.get_similar_tags(current)]


setup = Tag.setup
