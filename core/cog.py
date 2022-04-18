import asyncio
import logging
from typing import TYPE_CHECKING, Any
from discord.ext import commands, tasks

from typing_extensions import Self


if TYPE_CHECKING:
    from core.bot import BoboBot
    from discord.ext.commands import Cog


__all__ = ('Cog',)
__log__ = logging.getLogger('BoboBot')


class CogMeta(commands.CogMeta):
    if TYPE_CHECKING:
        __tasks__: list[tasks.Loop]


class MetaTask(CogMeta):
    """
    A simple Metclass that can be used to get all tasks.Loop from the class,
    to start and cancel them easily.
    """

    def __new__(cls, name: Any, bases: Any, attrs: Any, **kwargs: Any) -> Self:
        new_cls = super().__new__(cls, name, bases, attrs)
        _inner_tasks = []

        for _, value in attrs.items():
            if issubclass(value.__class__, tasks.Loop):
                _inner_tasks.append(value)

        new_cls.__tasks__ = _inner_tasks  # type: ignore

        return new_cls

    def _unload_tasks(cls) -> None:
        for task in cls.__tasks__:
            coro = task.__dict__.get('coro')
            if not coro:
                continue

            __log__.info(
                f'Stopping task {coro.__name__} after {task.current_loop} intervals.'
            )

            loop = asyncio.get_running_loop()
            _tasks = []

            if task.is_running():
                task.cancel()
                _tasks.append(task._task)

            loop.create_task(asyncio.gather(*_tasks))  # type: ignore

    def _load_tasks(cls, self) -> None:
        for task in cls.__tasks__:
            coro = task.__dict__.get('coro')

            if not coro:
                continue

            __log__.info(
                f'Stopping task {coro.__name__} after {task.current_loop} intervals.'
            )

            if not task.is_running():
                task.start(self)


class Cog(commands.Cog, metaclass=MetaTask):
    def __init__(self, bot: BoboBot) -> None:
        self.bot = bot
        self.__class__._load_tasks(self)

    async def unload(self) -> None:
        ...

    async def cog_unload(self) -> None:
        self.__class__._unload_tasks()
        await self.unload()

    @classmethod
    async def setup(cls, bot: BoboBot) -> None:
        await bot.add_cog(cls(bot))
