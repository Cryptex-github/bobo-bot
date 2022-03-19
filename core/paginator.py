# This is a modified version of https://github.com/oliver-ni/discord-ext-menus-views

from __future__ import annotations

from typing import TYPE_CHECKING, Iterable, Any

import discord

from discord.ext import menus  # type: ignore

from core.view import BaseView

if TYPE_CHECKING:
    from discord import Embed, Interaction
    from discord.ui import Button
    from asyncio import Task


class ViewMenu(menus.Menu):
    def __init__(self, *, auto_defer: bool = True, **kwargs):
        self.extra_component = kwargs.pop('extra_component', None)

        super().__init__(**kwargs)

        self.auto_defer: bool = auto_defer
        self.view: BaseView | None = None
        self.__tasks: list[Task] = []

    def build_view(self) -> BaseView | None:
        if not self.should_add_reactions():
            return None

        def make_callback(button: menus.Button):
            async def callback(interaction: Interaction):
                if self.auto_defer:
                    await interaction.response.defer()
                try:
                    if button.lock:
                        async with self._lock:
                            if self._running:
                                await button(self, interaction)
                    else:
                        await button(self, interaction)  # type: ignore
                except Exception as exc:
                    await self.on_menu_button_error(exc)

            return callback

        view = BaseView(timeout=self.timeout, user_id=self._author_id)

        for i, (emoji, button) in enumerate(self.buttons.items()):
            if button.action.__name__ == "stop_pages":
                style = discord.ButtonStyle.danger
            else:
                style = discord.ButtonStyle.secondary

            item = discord.ui.Button(style=style, emoji=emoji, row=i // 5)

            item.callback = make_callback(button)
            view.add_item(item)
        
        if self.extra_component:
            view.add_item(self.extra_component)

        self.view = view
        return view

    def add_button(self, button: menus.Button, *, react: bool = False):
        super().add_button(button)

        if react:
            if self.__tasks:

                async def wrapped():
                    self.buttons[button.emoji] = button
                    try:
                        await self.message.edit(view=self.build_view())
                    except discord.HTTPException:
                        raise

                return wrapped()

            async def dummy():
                raise menus.MenuError("Menu has not been started yet")

            return dummy()

    def remove_button(self, emoji, *, react=False):
        super().remove_button(emoji)

        if react:
            if self.__tasks:

                async def wrapped():
                    self.buttons.pop(emoji, None)
                    try:
                        await self.message.edit(view=self.build_view())
                    except discord.HTTPException:
                        raise

                return wrapped()

            async def dummy():
                raise menus.MenuError("Menu has not been started yet")

            return dummy()

    def clear_buttons(self, *, react=False):
        super().clear_buttons()

        if react:
            if self.__tasks:

                async def wrapped():
                    try:
                        await self.message.edit(view=None)
                    except discord.HTTPException:
                        raise

                return wrapped()

            async def dummy():
                raise menus.MenuError("Menu has not been started yet")

            return dummy()

    async def _internal_loop(self):
        self.__timed_out = False
        try:
            self.__timed_out = await self.view.wait() # type: ignore
        except Exception:
            pass
        finally:
            self._event.set()

            try:
                await self.finalize(self.__timed_out)
            except Exception:
                pass
            finally:
                self.__timed_out = False

            if self.bot.is_closed():
                return

            try:
                if self.delete_message_after:
                    return await self.message.delete()
                elif self.clear_reactions_after:
                    return await self.message.edit(view=None)
                else:
                    return await self.message.edit(view=self.view._disable_all()) # type: ignore
            except Exception:
                pass

    async def start(self, ctx, *, channel=None, wait=False):
        try:
            del self.buttons
        except AttributeError:
            pass

        self.bot = bot = ctx.bot
        self.ctx = ctx
        self._author_id = ctx.author.id
        channel = channel or ctx.channel
        is_guild = hasattr(channel, "guild")
        me = channel.guild.me if is_guild else ctx.bot.user
        permissions = channel.permissions_for(me)
        self._verify_permissions(ctx, channel, permissions)
        self._event.clear()
        msg = self.message
        if msg is None:
            self.message = msg = await self.send_initial_message(ctx, channel)

        if self.should_add_reactions():
            for task in self.__tasks:
                task.cancel()
            self.__tasks.clear()

            self._running = True
            self.__tasks.append(bot.loop.create_task(self._internal_loop()))

            if wait:
                await self._event.wait()

    def send_with_view(self, messageable, *args, **kwargs):
        return messageable.send(*args, **kwargs, view=self.build_view())
    
    def edit_with_view(self, *args, **kwargs):
        if message := self.message:
            return message.edit(*args, **kwargs, view=self.build_view())
        
        async def dummy():
            return
        
        return dummy()

    def stop(self):
        self._running = False
        for task in self.__tasks:
            task.cancel()
        self.__tasks.clear()


class ViewMenuPages(menus.MenuPages, ViewMenu):
    def __init__(self, source, **kwargs):
        self._source = source
        self.current_page = 0
        super().__init__(source, **kwargs)

    async def send_initial_message(self, ctx, channel):
        page = await self._source.get_page(0)
        kwargs = await self._get_kwargs_from_page(page)
        return await self.send_with_view(channel, **kwargs)
    
    async def edit_initial_message(self):
        page = await self._source.get_page(0)
        kwargs = await self._get_kwargs_from_page(page)
        return await self.edit_with_view(**kwargs)

class EmbedListPageSource(menus.ListPageSource):
    def __init__(self, entries: Iterable[Any], *, title: str = 'Paginator', per_page: int = 10) -> None:
        super().__init__(entries, per_page=per_page)
        
        self.title = title

    async def format_page(self, menu, entries) -> dict[str, Embed]:
        return {
            'embed': menu.ctx.embed(title=self.title, description='\n'.join(entries))
                .set_author(name=str(menu.ctx.author), icon_url=str(menu.ctx.author.display_avatar))
                .set_footer(
                    text=f'Page {menu.current_page + 1}/{self.get_max_pages()} Total Entries: {len(self.entries)}'
                )
        }
