import asyncio
from collections import defaultdict
from typing import AsyncGenerator

import discord
from discord.ext import commands

from core import Cog, ReactionRoleManager
from core.command import group
from core.context import BoboContext
from core.paginator import EmbedListPageSource, ViewMenuPages


class ReactionRoles(Cog):
    async def cog_load(self) -> None:
        self.cache = ReactionRoleManager(self.bot.redis)
        self.locks: defaultdict[int, asyncio.Lock] = defaultdict(asyncio.Lock)

        reaction_roles = await self.bot.db.fetch("SELECT * FROM reaction_roles")

        for rr in reaction_roles:
            await self.cache.add(rr['message_id'], rr['role_id'], rr['emoji'])

    @Cog.listener()
    async def on_raw_reaction_add(
        self, payload: discord.RawReactionActionEvent
    ) -> None:
        if not self.bot.is_ready():
            return

        assert self.bot.user is not None

        if payload.user_id == self.bot.user.id:
            return

        if not payload.guild_id:
            return

        if not hasattr(self, 'cache'):
            return

        if emojis_to_roles := await self.cache.get_message(payload.message_id):
            if role := emojis_to_roles.get(str(payload.emoji.id or payload.emoji.name)):
                async with self.locks[payload.message_id]:
                    try:
                        await self.bot.http.add_role(
                            payload.guild_id,
                            payload.user_id,
                            role,
                            reason='Bobo Bot Reaction Role',
                        )
                    except discord.Forbidden:
                        pass

    @Cog.listener()
    async def on_raw_reaction_remove(
        self, payload: discord.RawReactionActionEvent
    ) -> None:
        if not self.bot.is_ready():
            return

        assert self.bot.user is not None

        if payload.user_id == self.bot.user.id:
            return

        if not payload.guild_id:
            return

        if not hasattr(self, 'cache'):
            return

        if emojis_to_roles := await self.cache.get_message(payload.message_id):
            if role := emojis_to_roles.get(str(payload.emoji.id or payload.emoji.name)):
                async with self.locks[payload.message_id]:
                    try:
                        await self.bot.http.remove_role(
                            payload.guild_id,
                            payload.user_id,
                            role,
                            reason='Bobo Bot Reaction Role',
                        )
                    except discord.Forbidden:
                        pass

    @group(aliases=['rr', 'reactionroles'])
    @commands.guild_only()
    async def reactionrole(self, ctx: BoboContext) -> None:
        """Manage reaction roles."""
        await ctx.send_help(ctx.command)

    @reactionrole.command()
    @commands.guild_only()
    async def add(self, ctx: BoboContext) -> AsyncGenerator[str, None]:
        """
        Add a reaction role.
        """
        yield 'What channel is the reaction role message in?'

        channel = await self.bot.wait_for(
            'message',
            check=lambda m: m.author == ctx.author and m.channel == ctx.channel,
        )
        try:
            channel = await commands.TextChannelConverter().convert(
                ctx, channel.content
            )
        except commands.ChannelNotFound:
            yield 'That channel does not exist.'

            return

        yield 'What is the message ID of the message you want to add reaction roles to?'

        message = await self.bot.wait_for(
            'message',
            check=lambda m: m.author == ctx.author and m.channel == ctx.channel,
        )
        try:
            message_id = int(message.content)
            message = await channel.fetch_message(message_id)
        except (ValueError, commands.MessageNotFound):
            yield 'That message does not exist.'

            return

        reaction_message = await ctx.send(
            'What emoji do you want to add reaction roles to? React to this message.'
        )

        payload = await self.bot.wait_for(
            'raw_reaction_add',
            check=lambda payload: payload.message_id == reaction_message.id,
        )
        emoji = payload.emoji

        try:
            m = await ctx.send('testing emoji')
            await m.add_reaction(emoji)
            await m.delete()
        except discord.HTTPException:
            yield 'It seems like I do not have permission to add reactions to that message.'

            return

        yield 'Lastly, what role do you want to add?'

        role = await self.bot.wait_for(
            'message',
            check=lambda m: m.author == ctx.author and m.channel == ctx.channel,
        )

        try:
            role = await commands.RoleConverter().convert(ctx, role.content)
        except commands.RoleNotFound:
            yield 'That role does not exist.'

            return

        assert ctx.guild is not None

        await self.bot.db.execute(
            'INSERT INTO reaction_roles VALUES ($1, $2, $3, $4)',
            ctx.guild.id,
            message.id,
            str(emoji.id or emoji.name),
            role.id,
        )
        await self.cache.add(message.id, role.id, str(emoji.id or emoji.name))

        try:
            await message.add_reaction(emoji)
        except discord.HTTPException:
            yield 'It seems like I do not have permission to add reactions to that message.'

        yield f'Successfully added reaction role to channel: {channel.mention} with message ID: {message.id} and emoji: {str(emoji)} for role: {role.mention}.'

    @reactionrole.command(name='list')
    @commands.guild_only()
    async def list_(self, ctx: BoboContext) -> str | None:
        """
        List all reaction roles.
        """
        assert ctx.guild is not None

        reaction_roles = await self.bot.db.fetch(
            "SELECT * FROM reaction_roles WHERE guild_id = $1", ctx.guild.id
        )

        if not reaction_roles:
            return 'There are no reaction roles in this server.'

        def get_role_mention(_role: int) -> str:
            assert ctx.guild is not None

            role = ctx.guild.get_role(_role)

            if not role:
                return 'Role not found'

            return role.mention

        formatted = [
            (
                f'Message ID: {message_id} and emoji: {emoji if not emoji.isnumeric() else str(self.bot.get_emoji(emoji))}'
                f' for role: {get_role_mention(role)}\n'
            )
            for _, message_id, emoji, role in reaction_roles
        ]

        source = EmbedListPageSource(formatted, title='Reaction Roles in this server.')
        pages = ViewMenuPages(source=source)

        await pages.start(ctx)


setup = ReactionRoles.setup
