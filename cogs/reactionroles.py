import asyncio
from collections import defaultdict

import discord
from discord.ext import commands

from core import Cog, ReactionRoleManager
from core.context import BoboContext


class ReactionRoles(Cog):
    async def cog_setup(self) -> None:
        self.cache = ReactionRoleManager(self.bot.redis)
        self.locks: defaultdict[int, asyncio.Lock] = defaultdict(asyncio.Lock)

        reaction_roles = await self.bot.db.fetch("SELECT * FROM reaction_roles")

        for rr in reaction_roles:
            await self.cache.add(rr['message_id'], rr['role_id'], rr['emoji'])
    
    @Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        if payload.user_id == self.bot.user.id:
            return
        
        if not payload.guild_id:
            return
        
        if emojis_to_roles := await self.cache.get_message(payload.message_id):
            if role := emojis_to_roles.get(str(payload.emoji.id) or payload.emoji.name):
                async with self.locks[payload.message_id]:
                    try:
                        await self.bot.http.add_role(payload.guild_id, payload.user_id, role, 'Bobo Bot Reaction Role')
                    except discord.Forbidden:
                        pass
    
    @Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent) -> None:
        if payload.user_id == self.bot.user.id:
            return
        
        if not payload.guild_id:
            return
        
        if emojis_to_roles := await self.cache.get_message(payload.message_id):
            if role := emojis_to_roles.get(str(payload.emoji.id) or payload.emoji.name):
                async with self.locks[payload.message_id]:
                    try:
                        await self.bot.http.remove_role(payload.guild_id, payload.user_id, role, 'Bobo Bot Reaction Role')
                    except discord.Forbidden:
                        pass
    
    @commands.group()
    @commands.guild_only()
    async def reactionrole(self, ctx: BoboContext) -> None:
        """Manage reaction roles."""
        await ctx.send_help(ctx.command)
    
    @reactionrole.command()
    @commands.guild_only()
    async def add(self, ctx: BoboContext) -> None:
        """
        Add a reaction role.
        """
        await ctx.send('What channel is the reaction role message in?')

        channel = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author and m.channel == ctx.channel)
        try:
            channel = await commands.TextChannelConverter().convert(ctx, channel.content)
        except commands.ChannelNotFound:
            await ctx.send('That channel does not exist.')

            return
        
        await ctx.send('What is the message ID of the message you want to add reaction roles to?')

        message = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author and m.channel == ctx.channel)
        try:
            message_id = int(message.content)
            message = await channel.fetch_message(message_id)
        except (ValueError, commands.MessageNotFound):
            await ctx.send('That message does not exist.')

            return
        
        await ctx.send('What emoji do you want to add reaction roles to?')

        emoji = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author and m.channel == ctx.channel)

        try:
            emoji = await commands.PartialEmojiConverter().convert(ctx, emoji.content)
        except commands.PartialEmojiConversionFailure:
            await ctx.send('That emoji does not exist.')

            return
        
        try:
            m = await ctx.send('testing emoji')
            await m.add_reaction(emoji)
            await m.delete()
        except discord.HTTPException:
            await ctx.send('It seems like I do not have permission to add reactions to that message.')

            return
        
        await ctx.send('Lastly, what role do you want to add?')

        role = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author and m.channel == ctx.channel)

        try:
            role = await commands.RoleConverter().convert(ctx, role.content)
        except commands.RoleNotFound:
            await ctx.send('That role does not exist.')
            
            return
        
        if not ctx.guild: # Useless check just for the type checker
            raise RuntimeError('Guild not found') # Not possible since we have guild_only check
        
        await self.bot.db.execute('INSERT INTO reaction_roles VALUES ($1, $2, $3, $4)', ctx.guild.id, message.id, str(emoji.id or emoji.name), role.id)
        await self.cache.add(message.id, role.id, str(emoji.id or emoji.name))

        await ctx.send(f'Successfully added reaction role to channel: {channel.mention} with message ID: {message.id} and emoji: {str(emoji)} for role: {role.mention}.', allowed_mentions=discord.AllowedMentions.none())

setup = ReactionRoles.setup
