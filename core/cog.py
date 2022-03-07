import asyncio
import logging

import discord
from discord.ext import commands, tasks

__all__ = ('Cog',)
__log__ = logging.getLogger('BoboBot')


class MetaTask(commands.CogMeta):
    """
    A simple Metclass that can be used to get all tasks.Loop from the class,
    to start and cancel them easily.
    """

    def __new__(cls, name, bases, attrs, **kwargs):
        new_cls = super().__new__(cls, name, bases, attrs)
        _inner_tasks = []

        for key, value in attrs.items():
            if issubclass(value.__class__, tasks.Loop):
                _inner_tasks.append(value)

        new_cls.__tasks__ = _inner_tasks
        return new_cls

    def _unload_tasks(cls):
        for task in cls.__tasks__:
            coro = task.__dict__.get('coro')
            __log__.info(
                f'Stopping task {coro.__name__} after {task.current_loop} intervals.'
            )
            loop = asyncio.get_running_loop()
            _tasks = []
            if task.is_running():
                task.cancel()
                _tasks.append(task._task)
            loop.create_task(asyncio.gather(*_tasks))

    def _load_tasks(cls, self):
        for task in cls.__tasks__:
            coro = task.__dict__.get('coro')
            __log__.info(
                f'Stopping task {coro.__name__} after {task.current_loop} intervals.'
            )
            if not task.is_running():
                task.start(self)


class Cog(commands.Cog, metaclass=MetaTask):
    def __init__(self, bot):
        self.bot = bot
        self.__class__._load_tasks(self)
        coro = discord.utils.maybe_coroutine(self.init)
        self.bot.loop.create_task(coro)

    def init(self):
        pass

    def unload(self):
        pass

    def cog_unload(self):
        self.__class__._unload_tasks()
        self.unload()

    @classmethod
    def setup(cls, bot):
        bot.add_cog(cls(bot))
