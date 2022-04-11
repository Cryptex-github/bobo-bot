from __future__ import annotations
from functools import _Descriptor

from typing import TYPE_CHECKING, Any

import discord

from discord.ext.commands import HelpCommand, DefaultHelpCommand, CommandError, Context

from core.view import BaseView
from core.paginator import ViewMenuPages, EmbedListPageSource
from core.constants import INVITE_LINK, SUPPORT_SERVER


if TYPE_CHECKING:
    from core.cog import Cog
    from core.view import BaseView
    from core.context import BoboContext

    from discord import Interaction
    from discord.ext.commands import Command, Group


class BoboHelpSelect(discord.ui.Select[BaseView]):
    def __init__(
        self, ctx: Context, mapping: dict[Cog, list[Command[Cog, ..., Any]]]
    ) -> None:
        options = [
            discord.SelectOption(
                label=cog.qualified_name,
                description=f'View help for {cog.qualified_name} category.',
            )
            for cog in mapping.keys()
            if getattr(cog, 'ignore', False) is False
        ]

        options.insert(
            0,
            discord.SelectOption(
                label='Home', description='Go back to the main help menu.'
            ),
        )

        super().__init__(
            placeholder='Pick a category to learn more about it.',
            options=options,
            min_values=1,
            max_values=1,
        )

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
            await interaction.response.defer()

            source = EmbedListPageSource(
                BoboHelpCommand.get_cog_help(self.ctx, cog), title=cog.qualified_name
            )

            pages = ViewMenuPages(
                source=source, extra_component=self, message=interaction.message
            )

            await pages.start(self.ctx)



class BoboHelpCommand(HelpCommand[Context]):
    async def send_bot_help(
        self, mapping: dict[Cog | None, list[Command[Cog, ..., Any]]]
    ):
        try:
            del mapping[None]
        except KeyError:
            pass

        embed, view = self.get_bot_help(self.context, mapping)  # type: ignore

        await self.context.send(embed=embed, view=view)

    @staticmethod
    def get_bot_help(
        ctx: Context, mapping: dict[Cog, list[Command[Cog, ..., Any]]]
    ) -> tuple[discord.Embed, BaseView]:
        view = BaseView(user_id=ctx.author.id)

        view.add_item(BoboHelpSelect(ctx, mapping))

        embed = ctx.embed( # type: ignore
            title='Help Command',
            description=f'[Invite]({INVITE_LINK}) | [Support]({SUPPORT_SERVER})\n\n',
        )
        embed.add_field(name='Categories', value='\n'.join('**' + cog.qualified_name + '**' for cog in mapping.keys() if getattr(cog, 'ignore', False) is False), inline=False)
        embed.set_thumbnail(
            url='https://raw.githubusercontent.com/Roo-Foundation/roo/main/roos/rooThink.png'
        )

        return embed, view

    @staticmethod
    def format_commands(ctx: Context, commands: list[Command]) -> list[str]:
        formatted_commands = [
            f'**{ctx.clean_prefix}{command.qualified_name} {command.signature}**\n{command.description or command.short_doc or "No Help Provided"}\n\u200b'
            for command in commands
        ]

        return formatted_commands

    @staticmethod
    def get_cog_help(ctx: Context, cog: Cog) -> list[str]:
        commands = cog.get_commands()

        res = [f'Total Commands in this Cog: {len(commands)}\n\u200b']
        res += BoboHelpCommand.format_commands(ctx, commands)

        return res

    async def send_cog_help(self, cog: Cog):
        source = EmbedListPageSource(
            self.get_cog_help(self.context, cog), title=cog.qualified_name
        )

        pages = ViewMenuPages(source=source)

        await pages.start(self.context)

    async def send_command_help(self, command: Command[Any, ..., Any]) -> None:
        embed = self.context.embed( # type: ignore
            title=f'{self.context.clean_prefix}{command.qualified_name} {command.signature}'
        )
        embed.description = (
            command.description or command.short_doc or 'No Help Provided'
        )

        if bucket := getattr(command, '_buckets'):
            if cooldown := getattr(bucket, '_cooldown'):
                embed.add_field(
                    name='Cooldown',
                    value=f'{cooldown.rate} time(s) per {cooldown.per} second(s)',
                )

        embed.add_field(name='Category', value=command.cog_name)

        try:
            can_run = await command.can_run(self.context)
        except CommandError:
            can_run = False

        embed.add_field(name='Useable by you', value=str(can_run))
        embed.add_field(
            name='Usage', value=await self.context.get_command_usage(command) # type: ignore
        )
        embed.add_field(name='Aliases', value='\n'.join(command.aliases) or 'None')

        await self.context.send(embed=embed)

    async def send_group_help(self, group: Group[Any, ..., Any]) -> None:
        commands = list(group.walk_commands())

        res = [f'Total Commands in this Group: {len(commands)}\n\u200b']
        res += self.format_commands(self.context, commands)

        source = EmbedListPageSource(res, title=group.qualified_name)

        pages = ViewMenuPages(source=source)

        await pages.start(self.context)


async def setup(bot):
    bot.help_command = BoboHelpCommand()


async def teardown(bot):
    bot.help_command = DefaultHelpCommand()
