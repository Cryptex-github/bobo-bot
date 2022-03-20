from __future__ import annotations

from typing import TYPE_CHECKING, Iterable, Mapping, Any

import discord

from discord.ext.commands import HelpCommand, DefaultHelpCommand, CommandError
from core.context import BoboContext

from core.view import BaseView
from core.paginator import ViewMenuPages, EmbedListPageSource
from core.constants import INVITE_LINK, SUPPORT_SERVER

if TYPE_CHECKING:
    from core.cog import Cog

    from discord import Embed, Interaction
    from discord.ext.commands import Command

class BoboHelpSelect(discord.ui.Select):
    def __init__(self, ctx: BoboContext, mapping: dict[Cog, list[Command]]) -> None:
        options = [
            discord.SelectOption(label=cog.qualified_name, description=f'View help for {cog.qualified_name} category.') for cog in mapping.keys()
        ]

        options.insert(0, discord.SelectOption(label='Home', description='Go back to the main help menu.'))

        super().__init__(placeholder='Pick a category to learn more about it.', options=options, min_values=1, max_values=1)

        self.ctx = ctx

        self.mapping = mapping

        self.cog_mapping = {cog.qualified_name: cog for cog in mapping.keys()}
    
    async def callback(self, interaction: Interaction):
        try:
            cog = self.cog_mapping[self.values[0]]
        except KeyError:
            embed, view = BoboHelpCommand.get_bot_help(self.ctx, self.mapping)
            await interaction.response.edit_message(embed=embed, view=view)

            return
        else:
            source = EmbedListPageSource(BoboHelpCommand.get_cog_help(self.ctx, cog), title=cog.qualified_name)

            pages = ViewMenuPages(source=source, extra_component=self, message=interaction.message)

            await pages.start(self.ctx)

            await pages.edit_initial_message()



class BoboHelpCommand(HelpCommand):
    async def send_bot_help(self, mapping):
        embed, view = self.get_bot_help(self.context, mapping) # type: ignore
        
        await self.context.send(embed=embed, view=view)
    
    @staticmethod
    def get_bot_help(ctx: BoboContext, mapping: dict[Cog, list[Command]]) -> tuple[discord.Embed, BaseView]:
        view = BaseView(user_id=ctx.author.id)
        
        del mapping[None] # type: ignore

        view.add_item(BoboHelpSelect(ctx, mapping)) # type: ignore
        
        embed = ctx.embed(title='Help Command', description=f'[Invite]({INVITE_LINK}) | [Support]({SUPPORT_SERVER})\n\n') # type: ignore
        embed.add_field(name='Categories', value='\n'.join('**' + cog.qualified_name + '**' for cog in mapping.keys()), inline=False) # type: ignore
        embed.set_thumbnail(url='https://raw.githubusercontent.com/Roo-Foundation/roo/main/roos/rooThink.png')

        return embed, view
    
    @staticmethod
    def format_commands(ctx: BoboContext, commands: list[Command]) -> list[str]:
        formatted_commands = [
            f'**{ctx.clean_prefix}{command.qualified_name} {command.signature}**\n{command.description or command.short_doc or "No Help Provided"}\n\u200b' 
            for command in commands
            ]

        return formatted_commands

    @staticmethod
    def get_cog_help(ctx: BoboContext, cog: Cog) -> list[str]:
        commands = cog.get_commands()

        res = [f'Total Commands in this Cog: {len(commands)}\n\u200b'] 
        res += BoboHelpCommand.format_commands(ctx, commands)

        return res
    
    async def send_cog_help(self, cog: Cog):
        source = EmbedListPageSource(self.get_cog_help(self.context, cog), title=cog.qualified_name) # type: ignore

        pages = ViewMenuPages(source=source)

        await pages.start(self.context)
    
    async def send_command_help(self, command: Command[Any, ..., Any]) -> None:
        embed = self.context.embed(title=f'{self.context.clean_prefix}{command.qualified_name} {command.signature}') # type: ignore
        embed.description = command.description or command.short_doc or 'No Help Provided'

        if bucket := getattr(command, '_buckets'):
            if cooldown := getattr(bucket, '_cooldown'):
                embed.add_field(name='Cooldown', value=f'{cooldown.rate} time(s) per {cooldown.per} second(s)')
        
        embed.add_field(name='Category', value=command.cog_name)

        try:
            can_run = await command.can_run(self.context)
        except CommandError:
            can_run = False
        
        embed.add_field(name='Runnable by you', value=str(can_run))
        embed.add_field(name='Usage', value=await self.context.get_command_usage(command)) # type: ignore
        embed.add_field(name='Aliases', value='\n'.join(command.aliases) or 'None')

        await self.context.send(embed=embed)

async def setup(bot):
    bot.help_command = BoboHelpCommand()

async def teardown(bot):
    bot.help_command = DefaultHelpCommand()
        