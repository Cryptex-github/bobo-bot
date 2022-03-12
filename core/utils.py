import time
import re

__all__ = ('Timer', 'finder')

class Timer:
    def __init__(self):
        self._start = None
        self._end = None

    def start(self):
        self._start = time.perf_counter()

    def stop(self):
        self._end = time.perf_counter()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def __int__(self):
        return round(self.time)

    def __float__(self):
        return self.time

    def __str__(self):
        return str(self.time)

    def __repr__(self):
        return f"<Timer time={self.time}>"

    @property
    def time(self):
        if self._end is None:
            raise ValueError("Timer has not been ended.")
        return self._end - self._start

# Shamelessly robbed from R. Danny
def finder(text, collection, *, key=None, lazy=True):
    maybe = []
    text = str(text)
    to_compile = ".*?".join(map(re.escape, text))
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
