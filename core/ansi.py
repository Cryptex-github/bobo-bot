from __future__ import annotations

from enum import IntEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing_extensions import Self


class ANSIFormat(IntEnum):
    normal = 0
    bold = 1
    underline = 4


class ANSIColor(IntEnum):
    gray = 30
    red = 31
    green = 32
    yellow = 33
    blue = 34
    pink = 35
    cyan = 36
    white = 37


class ANSIBackgroundColor(IntEnum):
    dark_blue = 40
    orange = 41
    gray = 42
    light_gray = 43
    extra_light_gray = 44
    lndigo = 45
    slight_light_gray = 46
    white = 47


class ANSIBuilder:
    def __init__(self, initial_text: str = '') -> None:
        self.text = initial_text
        self.raw_text = initial_text

    @staticmethod
    def get_ansi_code(color: ANSIColor | None = None, background: ANSIBackgroundColor | None = None, bold: bool = False, underline: bool = False) -> str:
        parts = []
        
        if color:
            parts.append(str(color.value))
        if background:
            parts.append(str(background.value))
        if bold:
            parts.append(str(ANSIFormat.bold.value))
        if underline:
            parts.append(str(ANSIFormat.underline.value))
        
        if not parts:
            return ''
        
        return f'\u001b[{";".join(parts)}m'
    
    @property
    def clear_code(self) -> str:
        return '\u001b[0m'

    def append(self, text: str, **kwargs) -> Self:
        parts = self.get_ansi_code(**kwargs)

        if kwargs.pop('clear'):
            parts += '\u001b[0m'
        
        self.text += parts + text + self.clear_code
        self.raw_text += text

        return self
    
    def color(self, color: ANSIColor, text: str) -> Self:
        return self.append(text, color=color)
    
    def background_color(self, color: ANSIBackgroundColor, text: str) -> Self:
        return self.append(text, background=color)
    
    def bold(self, text: str) -> Self:
        return self.append(text, bold=True)
    
    def underline(self, text: str) -> Self:
        return self.append(text, underline=True)
    
    def build(self) -> str:
        return f'```ansi\n{self.text}\n```'
    
    def build_raw(self) -> str:
        return self.raw_text
