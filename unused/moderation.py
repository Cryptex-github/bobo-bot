from __future__ import annotations

from enum import IntEnum

from typing import TYPE_CHECKING

from discord.ext.commands import CooldownMapping, BucketType
from core.command import group
from core.cog import Cog

if TYPE_CHECKING:
    from core.context import BoboContext
    from discord import Message


class MessageCooldownMapping(CooldownMapping):
    def _bucket_key(self, message: Message) -> tuple[int, str]:
        return message.id, message.content


class AntiSpamConfig:
    def __init__(self, rate: float, per: float, action: IntEnum) -> None:
        self.rate = rate
        self.per = per
        self.action = action


class SpamCheckingManager:
    def __init__(self, config: AntiSpamConfig) -> None:
        self.from_message = MessageCooldownMapping.from_cooldown(
            config.rate, config.per, BucketType.member
        )


class Moderation(Cog):
    @Cog.listener()
    async def on_message(self, message: Message) -> None:
        ...

    @group()
    async def automod(self, ctx: BoboContext) -> None:
        ...
