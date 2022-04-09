from __future__ import annotations

from typing import TYPE_CHECKING
from io import BytesIO

from akinator.async_aki import Akinator
from akinator import CantGoBackAnyFurther
import discord

from core import Cog
from core.command import command, group
from core.view import BaseView
from core.utils import cutoff

if TYPE_CHECKING:
    from core.context import BoboContext
    from discord import Embed, Interaction
    from discord.ui import Button

    from core.types import OUTPUT_TYPE

    from typing import TypeVar

    EmbedT = TypeVar('EmbedT', bound=Embed)


class AkinatorOptionsView(BaseView):
    @discord.ui.button(
        label='Peoples', custom_id='en', style=discord.ButtonStyle.primary, emoji='👤'
    )
    async def peoples(
        self, interaction: discord.Interaction, button: discord.ui.Button
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
        self, interaction: discord.Interaction, button: discord.ui.Button
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
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.selected = button.custom_id

        await interaction.response.defer()

        self.stop()


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

        return '▓' * int(progress / value_per_block) + '░' * int(
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


class RedditCommentsView(BaseView):
    def __init__(self, comments: list[Embed], user_id: int, timeout: int = 180) -> None:
        super().__init__(user_id, timeout)

        self.comments = comments
        self.index = 0

    def handle_embed(self, embed: EmbedT) -> EmbedT:
        page_number = f'{self.index + 1}/{len(self.comments)}'

        embed.set_footer(
            text=f'{page_number} {embed.footer.text.replace(page_number, "").strip() if embed.footer and embed.footer.text else ""}'
        )

        return embed

    @discord.ui.button(emoji='⏮️')
    async def front(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.index = 0
        embed = self.handle_embed(self.comments[0])

        await interaction.response.edit_message(embed=embed)

    @discord.ui.button(emoji='◀️')
    async def backward(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.index -= 1

        if self.index < 0:
            self.index = 0

        embed = self.handle_embed(self.comments[self.index])

        await interaction.response.edit_message(embed=embed)

    @discord.ui.button(emoji='▶️')
    async def forward(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.index += 1

        if self.index >= len(self.comments):
            self.index = len(self.comments) - 1

        embed = self.handle_embed(self.comments[self.index])

        await interaction.response.edit_message(embed=embed)

    @discord.ui.button(emoji='⏭️')
    async def back(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.index = len(self.comments) - 1
        embed = self.handle_embed(self.comments[self.index])

        await interaction.response.edit_message(embed=embed)


class RedditView(BaseView):
    def __init__(self, comments: list[Embed], user_id: int, timeout: int = 180) -> None:
        super().__init__(user_id, timeout)

        self._comments = comments

    @discord.ui.button(label='Comments')
    async def comments(self, interaction: Interaction, button: Button) -> None:
        view = RedditCommentsView(self._comments, self.user_id)

        await interaction.response.edit_message(embed=view.handle_embed(self._comments[0]), view=view)


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
            return discord.File(BytesIO(await resp.read()), filename=f'{code}.png')
    
    @staticmethod
    def process_reddit_post(ctx, _js) -> OUTPUT_TYPE:
        js = _js[0]['data']['children'][0]['data']

        embed = ctx.embed(
            title=js['title'],
            description=cutoff(js['selftext'], max_length=4000),
            url='https://www.reddit.com' + js['permalink'],
        )
        embed.set_author(
            name='u/' + js['author'],
            url='https://www.reddit.com/user/' + js['author'],
        )

        embed.set_footer(
            text=f'\U0001f815 {js["ups"]} | {js["num_comments"]} comments | r/{js["subreddit"]}'
        )

        if image_url := js.get('url_overridden_by_dest'):
            if 'v.redd.it' not in image_url:
                embed.set_image(url=image_url)

        if comments := _js[1]['data']['children']:
            embeds = [
                ctx.embed(
                    description=cutoff(c['data']['body'], max_length=4000),
                    url='https://www.reddit.com' + c['data']['permalink'],
                ).set_footer(
                    text=f'\U0001f815 {c["data"]["ups"]} | {js["num_comments"]} comments | r/{js["subreddit"]}'
                )
                .set_author(name='u/' + c['data']['author'], url='https://www.reddit.com/user/' + c['data']['author'])
                for c in comments
                if c['data'].get('permalink')
            ]

            view = RedditView(embeds, ctx.author.id)

            return embed, view

        return embed

    @group(aliases=['r'])
    async def reddit(self, ctx: BoboContext, url: str | None = None) -> OUTPUT_TYPE:
        if not url:
            return await ctx.send_help(ctx.command)

        if not url.startswith('https://www.reddit.com'):
            return 'Invalid Reddit URL'

        async with self.bot.session.get(url + '.json?raw_json=1') as resp:
            if resp.status != 200:
                return 'Invalid Reddit URL or Reddit is down'

            return self.process_reddit_post(ctx, await resp.json())

    @reddit.command(name='random', aliases=['r'])
    async def reddit_random(self, ctx, subreddit: str) -> OUTPUT_TYPE:
        async with self.bot.session.get(f'https://www.reddit.com/r/{subreddit}/random.json?raw_json=1') as resp:
            if resp.status != 200:
                return 'Invalid subreddit'
            
            return self.process_reddit_post(ctx, await resp.json())

setup = Fun.setup
