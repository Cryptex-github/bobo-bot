from __future__ import annotations

from typing import TYPE_CHECKING, Iterable

import discord

from discord.ext.commands import HelpCommand, DefaultHelpCommand

from core import BaseView

if TYPE_CHECKING:
    from discord import Interaction

class BoboHelpSelect(discord.ui.Select):
    def __init__(self, cogs: Iterable[str]) -> None:
        options = [
            discord.SelectOption(label=cog, description=f'View help for {cog} category.') for cog in cogs
        ]

        super().__init__(placeholder='Pick a category to learn more about it.', options=options, min_values=1, max_values=1)
    
    async def callback(self, interaction: Interaction):
        self.view.selected = self.values[0]

        await interaction.defer()


class BoboHelpCommand(HelpCommand):
    async def send_bot_help(self, mapping):
        self.view = view = BaseView(user_id=self.context.user.id)

        cogs = sorted(mapping.keys())

        view.add_item(BoboHelpSelect(map(lambda cog: cog.qualified_name, cogs)))
        
        embed = self.context.embed(title='Help Command', description='Invite | Support\n\n')
        embed.add_field(name='Categories', value='\n'.join(cogs), inline=False)
        embed.set_thumbnail(url='https://raw.githubusercontent.com/Roo-Foundation/roo/main/roos/rooThink.png')
        
        await self.context.send(embed=embed, view=view)


async def setup(bot):
    bot.help_command = BoboHelpCommand()

async def teardown(bot):
    bot.help_command = DefaultHelpCommand()
        