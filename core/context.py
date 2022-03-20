from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from .view import ConfirmView, BaseView
from .button import DeleteButton

if TYPE_CHECKING:
    from typing import Any
    from core.command import BoboBotCommand

__all__ = ('BoboContext',)

class BoboContext(commands.Context): # type: ignore
    async def confirm(self, content: str | None = None, timeout: int = 60, **kwargs: Any) -> bool:
        view = ConfirmView(timeout=timeout, user_id=self.author.id)
        await self.send(content, view=view, **kwargs)
        await view.wait()

        return bool(view.value)

    async def paste(self, content: Any) -> str:
        return str(await self.bot.mystbin.post(str(content)))
    
    async def get_command_usage(self, command: BoboBotCommand) -> int:
        return await self.bot.db.fetchval('SELECT uses FROM commands_usage WHERE command = $1;', command.qualified_name)
    
    async def inicrease_command_usage(self, command: BoboBotCommand) -> int:
        return await self.bot.db.fetchval('INSERT INTO commands_usage VALUES ($1) ON CONFLICT (command) DO UPDATE SET uses = commands_usage.uses + 1 RETURNING uses;', command.qualified_name)

    async def send(self, content: str | None = None, **kwargs: Any) -> discord.Message:
        codeblock = kwargs.pop('codeblock', False)
        lang = kwargs.pop('lang', 'py')
        can_delete = kwargs.pop('can_delete', False)

        if can_delete:
            view = kwargs.get('view', BaseView(self.author.id))
            view.add_item(DeleteButton(self.author.id))
            kwargs['view'] = view

        if codeblock:
            content = f'```{lang}\n' + str(content) + '\n```'
        
        if self.message.edited_at:
            if message := await self.bot.delete_message_manager.get_messages(self.message.id, True):
                if 'file' in kwargs or 'files' in kwargs:
                    # Can't edit message to send file, so send a new message.
                    m = await super().send(content, **kwargs)
                    await self.bot.delete_message_manager.add_message(self.message.id, m.id)

                    return m
                
                m = self.channel.get_partial_message(message)  # type: ignore

                return await m.edit(content=content, **kwargs)

        m = await super().send(content, **kwargs)
        await self.bot.delete_message_manager.add_message(self.message.id, m.id)

        return m
    
    async def reply(self, content: str | None = None, **kwargs: Any) -> discord.Message:
        kwargs['reference'] = self.message

        return await self.send(content, **kwargs)
    
    def embed(self, **kwargs) -> discord.Embed:
        if 'color' not in kwargs:
            kwargs['color'] = self.bot.color

        return discord.Embed(**kwargs)
