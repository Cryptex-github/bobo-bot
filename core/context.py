import discord
from discord.ext import commands

from .view import ConfrimView
from .button import DeleteButton


class BoboContext(commands.Context):
    async def confrim(self, content=None, timeout=60, **kwargs):
        view = ConfrimView(timeout=timeout, user_id=self.author.id)
        await self.send(content, view=view, **kwargs)
        await view.wait()

        return bool(view.value)

    async def paste(self, content):
        return str(await self.bot.mystbin.post(str(content)))

    async def send(self, content=None, **kwargs):
        codeblock = kwargs.pop('codeblock', False)
        lang = kwargs.pop('lang', 'py')
        can_delete = kwargs.pop('can_delete', False)

        if can_delete:
            view = kwargs.get('view', discord.ui.View())
            view.add_item(DeleteButton(self.user.id))
            kwargs['view'] = view

        if codeblock:
            content = f'```{lang}\n' + str(content) + '\n```'

        return await super().send(content, **kwargs)
