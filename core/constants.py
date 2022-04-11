import re

__all__ = ('Regexs')

class Regexs:
    FILES_TO_RELOAD_REGEX = re.compile(r'\w+/[a-z]+\.py')
    SPHINX_ENTRY_REGEX = re.compile(r"(?x)(.+?)\s+(\S*:\S*)\s+(-?\d+)\s+(\S+)\s+(.*)")
    URL_REGEX = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
