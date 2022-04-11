from __future__ import annotations

from typing import TYPE_CHECKING
from io import BytesIO

from akinator.async_aki import Akinator
from akinator import CantGoBackAnyFurther
import discord

from core import Cog, command
from core.view import BaseView

if TYPE_CHECKING:
    from core.context import BoboContext


class AkinatorOptionsView(BaseView):
    @discord.ui.button(
        label='Peoples', custom_id='en', style=discord.ButtonStyle.primary, emoji='👤'
    )
    async def peoples(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ) -> None:
        self.selected = button.custom_id

        await interaction.response.defer()

        self.stop()

    @discord.ui.button(
        label='Animals',
        custom_id='en_animals',
        style=discord.ButtonStyle.primary,
        emoji='🐶',
    )
    async def animals(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ) -> None:
        self.selected = button.custom_id

        await interaction.response.defer()

        self.stop()

    @discord.ui.button(
        label='Objects',
        custom_id='en_objects',
        style=discord.ButtonStyle.primary,
        emoji='🏠',
    )
    async def objects(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ) -> None:
        self.selected = button.custom_id

        await interaction.response.defer()


class AkinatorView(BaseView):
    controls = {
        '\U00002705': 'yes',
        '\U0000274c': 'no',
        '\U00002753': 'idk',
        '\U0001f615': 'probably',
        '\U0001f61e': 'probably not',
        '\U000025c0': 'back',
        '\U000023f9': 'stop',
    }

    def __init__(self, user_id: int, timeout: int = 180) -> None:
        super().__init__(user_id, timeout)

        async def callback(interaction: discord.Interaction) -> None:
            if interaction.data:
                await self.process_interaction(
                    interaction, interaction.data.get('custom_id', '')
                )

                return

            await interaction.response.defer()

        for k, v in self.controls.items():
            button = discord.ui.Button(
                style=discord.ButtonStyle.secondary, emoji=k, label=v, custom_id=v
            )
            button.callback = callback

            self.add_item(button)

    def make_progress_bar(self) -> str:
        total_value = 100
        value_per_block = 5
        progress = self.akinator.progression

        return "▓" * int(progress / value_per_block) + "░" * int(
            (total_value / value_per_block) - (progress / value_per_block)
        )

    def make_embed(self, question: str) -> discord.Embed:
        embed = self.embed(title='Akinator', description=self.make_progress_bar())

        embed.add_field(name=f'Question {self.akinator.step + 1}', value=question)

        embed.set_thumbnail(
            url='https://en.akinator.com/bundles/elokencesite/images/akinator.png?v94'
        )

        return embed

    async def process_interaction(
        self, interaction: discord.Interaction, custom_id: str
    ) -> None:
        if custom_id == 'back':
            try:
                await self.akinator.back()
            except CantGoBackAnyFurther:
                pass

            await interaction.response.defer()

        elif custom_id == 'stop':
            await self.disable_all(interaction)

            self.stop()

        elif self.akinator.progression > 80:
            await self.akinator.win()

            guessed = self.akinator.first_guess

            embed = self.embed(
                title=guessed['name'], description=guessed['description']
            )
            embed.set_thumbnail(
                url='https://en.akinator.com/bundles/elokencesite/images/akinator.png?v94'
            )
            embed.set_image(url=guessed['absolute_picture_path'])

            await interaction.response.edit_message(
                embed=embed, view=self._disable_all()
            )

        else:
            question = await self.akinator.answer(custom_id)

            embed = self.make_embed(question)

            await interaction.response.edit_message(embed=embed)

    async def start(self, ctx: BoboContext, selected: str) -> discord.Embed:
        self.akinator = Akinator()
        self.embed = ctx.embed

        if ctx.guild:
            question = await self.akinator.start_game(language=selected, client_session=ctx.bot.session, child_mode=not ctx.channel.is_nsfw())  # type: ignore
        else:
            question = await self.akinator.start_game(
                language=selected, client_session=ctx.bot.session, child_mode=False
            )

        embed = self.make_embed(question)

        return embed


class Fun(Cog):
    @command()
    async def akinator(self, ctx: BoboContext) -> None:
        embed = ctx.embed(title='Akinator', description='What do you want me to guess?')
        embed.set_thumbnail(
            url='https://en.akinator.com/bundles/elokencesite/images/akinator.png?v94'
        )

        view = AkinatorOptionsView(user_id=ctx.author.id)
        m = await ctx.send(embed=embed, view=view)

        if await view.wait():
            return

        await m.edit(view=view._disable_all())

        akinator_view = AkinatorView(user_id=ctx.author.id)
        embed = await akinator_view.start(ctx, view.selected)  # type: ignore

        await m.edit(embed=embed, view=akinator_view)

        await akinator_view.wait()

    @command()
    async def http(self, ctx: BoboContext, code: int) -> discord.File:
        async with self.bot.session.get(f'https://http.cat/{code}') as resp:
            return discord.File(await resp.read(), filename=f'{code}.png')


setup = Fun.setup
