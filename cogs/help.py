from __future__ import annotations

from typing import TYPE_CHECKING, Iterable

import discord

from discord.ext.commands import HelpCommand, DefaultHelpCommand
from core.context import BoboContext

from core.view import BaseView
from core.paginator import ViewMenuPages, EmbedListPageSource

if TYPE_CHECKING:
    from core.cog import Cog

    from discord import Embed, Interaction
    from discord.ext.commands import Command

class BoboHelpSelect(discord.ui.Select):
    def __init__(self, ctx: BoboContext, mapping: dict[Cog, list[Command]]) -> None:
        options = [
            discord.SelectOption(label=cog.qualified_name, description=f'View help for {cog.qualified_name} category.') for cog in mapping.keys()
        ]

        super().__init__(placeholder='Pick a category to learn more about it.', options=options, min_values=1, max_values=1)

        self.ctx = ctx

        self.mapping = mapping

        self.cog_mapping = {cog.qualified_name: cog for cog in mapping.keys()}
    
    async def callback(self, interaction: Interaction):
        try:
            cog = self.cog_mapping[self.values[0]]
            print('cog')
        except KeyError:
            embed, view = BoboHelpCommand.get_bot_help(self.ctx, self.mapping)
            print('bot help')
            await interaction.response.edit_message(embed=embed, view=view)

            return
        else:
            source = EmbedListPageSource(BoboHelpCommand.get_cog_help(self.ctx, cog), title=cog.qualified_name)

            pages = ViewMenuPages(source=source, extra_component=self, message=interaction.message)

            await pages.start(self.ctx)
            print('started pages')



class BoboHelpCommand(HelpCommand):
    async def send_bot_help(self, mapping):
        embed, view = self.get_bot_help(self.context, mapping) # type: ignore
        
        await self.context.send(embed=embed, view=view)
    
    @staticmethod
    def get_bot_help(ctx: BoboContext, mapping: dict[Cog, list[Command]]) -> tuple[discord.Embed, BaseView]:
        view = BaseView(user_id=ctx.author.id)
        
        del mapping[None] # type: ignore

        view.add_item(BoboHelpSelect(ctx, mapping)) # type: ignore
        
        embed = ctx.embed(title='Help Command', description='Invite | Support\n\n') # type: ignore
        embed.add_field(name='Categories', value='\n'.join(cog.qualified_name for cog in mapping.keys()), inline=False) # type: ignore
        embed.set_thumbnail(url='https://raw.githubusercontent.com/Roo-Foundation/roo/main/roos/rooThink.png')

        return embed, view
    
    @staticmethod
    def format_commands(ctx: BoboContext, commands: list[Command]) -> list[str]:
        formatted_commands = [
            f'{ctx.clean_prefix}{command.qualified_name} {command.signature}\n{command.description or command.short_doc or "No Help Provided"}' 
            for command in commands
            ]

        return formatted_commands

    @staticmethod
    def get_cog_help(ctx: BoboContext, cog: Cog) -> list[str]:
        commands = cog.get_commands()

        res = [f'Total Commands in this Cog: {len(commands)}'] 
        res += BoboHelpCommand.format_commands(ctx, commands)

        return res


async def setup(bot):
    bot.help_command = BoboHelpCommand()

async def teardown(bot):
    bot.help_command = DefaultHelpCommand()
        