from abc import ABC
from typing import Final, TypeAlias
import re
from re import Pattern


__all__ = ('Regexes',)

RePattern: TypeAlias = Final[Pattern[str]]


class Regexes:
    FILES_TO_RELOAD_REGEX: RePattern = re.compile(r'\w+/[a-z_]+\.py')
    SPHINX_ENTRY_REGEX: RePattern = re.compile(
        r"(?x)(.+?)\s+(\S*:\S*)\s+(-?\d+)\s+(\S+)\s+(.*)"
    )
    URL_REGEX: RePattern = re.compile(
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    )
    TENOR_REGEX: RePattern = re.compile(r'http[s]?://(www\.)?tenor\.com/view/\S+/')
    TENOR_MEDIA_REGEX: RePattern = re.compile(r'http[s]?:\/\/c.tenor.com/\w+\/[a-zA-z-]+\.gif')
    GIPHY_REGEX: RePattern = re.compile(r'http[?://(www\.)?giphy\.com/gifs/[A-Za-z0-9]+/?')


INVITE_LINK: Final[str] = (
    r'https://discord.com/api/oauth2/authorize?client_id=808485782067216434&permissions=448827607232&scope=bot%20applications.commands'
)
SUPPORT_SERVER: Final[str] = 'https://discord.gg/AHYTRPr8hZ'
BOT_COLOR: Final[int] = 0xFF4500
BETA_ID: Final[int] = 808485782067216434
PROD_ID: Final[int] = 787927476177076234

class Constant(ABC):
    __slots__ = ()


class _Reply(Constant):
    __slots__ = ()


class _CanDelete(Constant):
    __slots__ = ()


class _SafeSend(Constant):
    __slots__ = ()


REPLY: Final[_Reply] = _Reply()
CAN_DELETE: Final[_CanDelete] = _CanDelete()
SAFE_SEND: Final[_SafeSend] = _SafeSend()
