from abc import ABC
import re


__all__ = ('Regexs',)


class Regexs:
    FILES_TO_RELOAD_REGEX = re.compile(r'\w+/[a-z]+\.py')
    SPHINX_ENTRY_REGEX = re.compile(r"(?x)(.+?)\s+(\S*:\S*)\s+(-?\d+)\s+(\S+)\s+(.*)")
    URL_REGEX = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')

INVITE_LINK = r'https://discord.com/api/oauth2/authorize?client_id=808485782067216434&permissions=448827607232&scope=bot%20applications.commands'
SUPPORT_SERVER = 'https://discord.gg/AHYTRPr8hZ'

class Constant(ABC):
    __slots__ = ()


class _Reply(Constant):
    __slots__ = ()


class _CanDelete(Constant):
    __slots__ = ()


class _SafeSend(Constant):
    __slots__ = ()


REPLY = _Reply()
CAN_DELETE = _CanDelete()
SAFE_SEND = _SafeSend()
