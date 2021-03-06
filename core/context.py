from __future__ import annotations

from typing import TYPE_CHECKING

from io import BytesIO

import discord
from discord.ext import commands

from .view import ConfirmView, BaseView
from .button import DeleteButton
from .constants import BOT_COLOR

if TYPE_CHECKING:
    from typing import Any
    from core.bot import BoboBot

__all__ = ('BoboContext',)


class BoboContext(commands.Context['BoboBot']):
    async def confirm(
        self, content: str | None = None, timeout: int = 60, **kwargs: Any
    ) -> bool:
        view = ConfirmView(timeout=timeout, user_id=self.author.id)
        await self.send(content, view=view, **kwargs)
        await view.wait()

        return bool(view.value)

    async def paste(self, content: Any) -> str:
        content = str(content)

        res = await self.bot.cdn.safe_upload(
            BytesIO(content.encode('utf-8')), extension='txt', directory='bobo_paste'
        )

        if res:
            return res.paste_url

        return str(await self.bot.mystbin.post(content))

    async def get_command_usage(self, command_name: str) -> int:
        return await self.bot.db.fetchval(
            'SELECT uses FROM commands_usage WHERE command = $1;',
            command_name,
        )

    async def inicrease_command_usage(self, command_name: str) -> int:
        return await self.bot.db.fetchval(
            'INSERT INTO commands_usage VALUES ($1) ON CONFLICT (command) DO UPDATE SET uses = commands_usage.uses + 1 RETURNING uses;',
            command_name,
        )

    async def send(self, content: str | None = None, **kwargs: Any) -> discord.Message:
        codeblock = kwargs.pop('codeblock', False)
        lang = kwargs.pop('lang', 'py')
        can_delete = kwargs.pop('can_delete', False)
        safe_send = kwargs.pop('safe_send', False)

        if can_delete:
            view = kwargs.get('view', BaseView(self.author.id))
            view.add_item(DeleteButton(self.author.id))
            kwargs['view'] = view

        if safe_send and content:
            if len(content) > 2000:
                content = await self.paste(content)

        if codeblock:
            content = f'```{lang}\n' + str(content) + '\n```'

        if self.message.edited_at:
            if message := await self.bot.delete_message_manager.get_messages(
                self.message.id, True
            ):
                if 'file' in kwargs or 'files' in kwargs:
                    # Can't edit message to send file, so send a new message.
                    m = await super().send(content, **kwargs)
                    await self.bot.delete_message_manager.add_message(
                        self.message.id, m.id
                    )

                    return m

                m = self.channel.get_partial_message(message[0])  # type: ignore

                return await m.edit(content=content, **kwargs)

        m = await super().send(content, **kwargs)
        await self.bot.delete_message_manager.add_message(self.message.id, m.id)

        return m

    async def reply(self, content: str | None = None, **kwargs: Any) -> discord.Message:
        kwargs['reference'] = self.message

        return await self.send(content, **kwargs)

    def embed(self, **kwargs) -> discord.Embed:
        if 'color' not in kwargs:
            kwargs['color'] = BOT_COLOR

        return discord.Embed(**kwargs)
