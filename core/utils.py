from __future__ import annotations

import asyncio
import functools
import time
import re

from typing import (
    TYPE_CHECKING,
    Awaitable,
    Any,
    Callable,
    TypeVar,
    ParamSpec,
    Iterable,
    Generator,
)

if TYPE_CHECKING:
    from typing_extensions import Self

__all__ = ('Instant', 'finder', 'async_executor', 'unique_list')

R = TypeVar('R')
P = ParamSpec('P')
T = TypeVar('T')
U = TypeVar('U')


class Duration:
    __slots__ = ('_time',)

    def __init__(self, time: float) -> None:
        self._time = time

    @classmethod
    def from_secs(cls, secs: float) -> Duration:
        return cls(secs)

    def as_nanos(self) -> float:
        return self._time * 1e9

    def as_micros(self) -> float:
        return self._time * 1e6

    def as_millis(self) -> float:
        return self._time * 1e3

    def as_secs(self) -> float:
        return self._time


class Instant:
    __slots__ = ('_start', '_end')

    def __init__(self) -> None:
        self._start: float | None = None
        self._end: float | None = None

    def start(self) -> None:
        self._start = time.perf_counter()

    @classmethod
    def now(cls) -> Self:
        instant = cls()
        instant.start()

        return instant

    def stop(self) -> None:
        self._end = time.perf_counter()

    @property
    def elapsed(self) -> Duration:
        return Duration.from_secs(self.time)

    def __enter__(self) -> Self:
        self.start()

        return self

    def __exit__(self, *args: Any, **kwargs: Any) -> None:
        self.stop()

    def __int__(self) -> int:
        return round(self.time)

    def __float__(self) -> float:
        return self.time

    def __str__(self) -> str:
        return str(self.time)

    def __repr__(self) -> str:
        return f"<Instant time={self.time}>"

    @property
    def time(self) -> float:
        if self._end is None:
            raise ValueError('Instant has not been ended.')
        if self._start is None:
            raise ValueError('Instant has not been started.')

        return self._end - self._start


# Shamelessly robbed from R. Danny
def finder(
    text: str,
    collection: Iterable[T],
    *,
    key: Callable[[T], U] | None = None,
    lazy: bool = True,
) -> list[T | U] | Generator[T | U, None, None]:
    maybe = []
    to_compile = '.*?'.join(map(re.escape, text))

    regex = re.compile(to_compile, flags=re.IGNORECASE)

    for item in collection:
        to_search = key(item) if key else item
        r = regex.search(to_search)
        if r:
            maybe.append((len(r.group()), r.start(), item))

    def sort_(var):
        if key:
            return var[0], var[1], key(var[2])
        return var

    if lazy:
        return (z for _, _, z in sorted(maybe, key=sort_))

    return [z for _, _, z in sorted(maybe, key=sort_)]


def async_executor(func: Callable[P, R]) -> Callable[P, Awaitable[R]]:
    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> Awaitable[R]:
        partial = functools.partial(func, *args, **kwargs)

        loop = asyncio.get_running_loop()
        return loop.run_in_executor(None, partial)

    return wrapper


def unique_list(seq: list[T]) -> list[T]:
    unique = []

    for item in seq:
        if item not in unique:
            unique.append(item)

    return unique


def cutoff(text: str, *, max_length: int = 2000) -> str:
    if len(text) > max_length:
        return text[: max_length - 1] + '…'

    return text
