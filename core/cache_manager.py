from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from redis.asyncio.client import Redis
    from discord.types.snowflake import SnowflakeList

    from .types import PossibleRTFMSources

__all__ = (
    'DeleteMessageManager',
    'RTFMCacheManager',
    'ReactionRoleManager',
    'PrefixManager',
)


class CacheManager(ABC):
    __slots__ = ()


class RedisCacheManager(CacheManager):
    __slots__ = ('redis',)

    def __init__(self, redis: Redis) -> None:
        self.redis = redis


class DeleteMessageManager(RedisCacheManager):
    __slots__ = ()

    async def get_messages(
        self, message_id: int, one_only: bool = False
    ) -> SnowflakeList:
        return [
            int(i)
            for i in await self.redis.lrange(
                f'delete_messages:{message_id}', 0, 0 if one_only else -1
            )
        ]

    async def add_message(self, message_id: int, message_maybe_delete: int) -> None:
        await self.redis.lpush(f'delete_messages:{message_id}', message_maybe_delete)

        await self.redis.expire(f'delete_messages:{message_id}', 86400)

    async def remove_message(self, message_id: int, message_to_delete: int) -> None:
        await self.redis.lrem(f'delete_messages:{message_id}', 0, message_to_delete)

    async def delete_messages(self, message_id: int) -> None:
        await self.redis.delete(f'delete_messages:{message_id}')


class RTFMCacheManager(RedisCacheManager):
    __slots__ = ()

    async def add(
        self, source: PossibleRTFMSources, query: str, nodes: dict[str, str]
    ) -> None:
        await self.redis.hmset(f'rtfm:{source}:{query}', nodes)

        await self.redis.expire(f'rtfm:{source}:{query}', 86400)

    async def get(
        self, source: PossibleRTFMSources, query: str
    ) -> dict[str, str] | None:
        return (
            await self.redis.hgetall(f'rtfm:{source}:{query}')
        ) or None  # If it returns empty Dict, returns None.


class ReactionRoleManager(RedisCacheManager):
    __slots__ = ()

    async def add(self, message_id: int, role_id: int, emoji: str) -> None:
        await self.redis.hset(f'reaction_roles:{message_id}', emoji, role_id)

    async def get_message(self, message_id: int) -> dict[str, int]:
        return {
            k: int(v)
            for k, v in (
                await self.redis.hgetall(f'reaction_roles:{message_id}')
            ).items()
        }

    async def delete(self, message_id: int) -> None:
        await self.redis.delete(f'reaction_roles:{message_id}')


class PrefixManager(RedisCacheManager):
    __slots__ = ()

    async def get_prefix(self, guild_id: int) -> list[str]:
        return await self.redis.lrange(f'prefix:{guild_id}', 0, -1)

    async def add_prefix(self, guild_id: int, *prefix: str) -> None:
        await self.redis.lpush(f'prefix:{guild_id}', *prefix)

    async def reset_prefix(self, guild_id: int) -> None:
        await self.redis.delete(f'prefix:{guild_id}')

    async def remove_prefix(self, guild_id: int, prefix: str) -> None:
        await self.redis.lrem(f'prefix:{guild_id}', 0, prefix)

    async def remove_prefixes(self, guild_id: int, *prefixes: str) -> None:
        async with self.redis.pipeline() as pipe:
            for prefix in prefixes:
                pipe.lrem(f'prefix:{guild_id}', 0, prefix)

            await pipe.execute()
