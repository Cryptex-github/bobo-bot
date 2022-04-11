import discord
from discord.ext import commands

from .button import DeleteButton
from .view import ConfrimView

__all__ = ("BoboContext",)


class BoboContext(commands.Context):
    async def confrim(self, content=None, timeout=60, **kwargs):
        view = ConfrimView(timeout=timeout, user_id=self.author.id)
        await self.send(content, view=view, **kwargs)
        await view.wait()

        return bool(view.value)

    async def paste(self, content):
        return str(await self.bot.mystbin.post(str(content)))

    async def send(self, content=None, **kwargs):
        codeblock = kwargs.pop("codeblock", False)
        lang = kwargs.pop("lang", "py")
        can_delete = kwargs.pop("can_delete", False)

        if can_delete:
            view = kwargs.get("view", discord.ui.View())
            view.add_item(DeleteButton(self.user.id))
            kwargs["view"] = view

        if codeblock:
            content = f"```{lang}\n" + str(content) + "\n```"

        return await super().send(content, **kwargs)

    def embed(self, **kwargs):
        if "color" not in kwargs:
            kwargs["color"] = self.bot.color

        return discord.Embed(**kwargs)
