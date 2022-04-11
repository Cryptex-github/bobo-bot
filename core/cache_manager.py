from typing import List

from abc import ABC
from typing import TYPE_CHECKING, List, Literal, Dict

if TYPE_CHECKING:
    from aioredis import Redis
    from .types import POSSIBLE_RTFM_SOURCES

__all__ = ('DeleteMessageManager', 'RTFMCacheManager', 'ReactionRoleManager')


class CacheManager(ABC):
    __slots__ = ()


class RedisCacheManager(CacheManager):
    __slots__ = ('redis',)

    def __init__(self, redis: Client) -> None:
        self.redis = redis


class DeleteMessageManager(RedisCacheManager):
    __slots__ = ()

    async def get_messages(self, message_id: int, one_only: bool = False) -> List[int]:
        return list(
            map(
                int,
                await self.redis.lrange(
                    f'delete_messages:{message_id}', 0, 0 if one_only else -1
                ),
            )
        )

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
        self, source: POSSIBLE_RTFM_SOURCES, query: str, nodes: Dict[str, str]
    ) -> None:
        await self.redis.hmset(f'rtfm:{source}:{query}', nodes)

        await self.redis.expire(f'rtfm:{source}:{query}', 86400)

    async def get(
        self, source: POSSIBLE_RTFM_SOURCES, query: str
    ) -> Dict[str, str] | None:
        return (
            await self.redis.hgetall(f'rtfm:{source}:{query}')
        ) or None  # If it returns empty Dict, returns None.


class ReactionRoleManager(RedisCacheManager):
    __slots__ = ()

    async def add(self, message_id: int, role_id: int, emoji: str) -> None:
        await self.redis.hset(f'reaction_roles:{message_id}', emoji, role_id)

    async def get_message(self, message_id: int) -> Dict[str, int]:
        return {
            k: int(v)
            for k, v in (
                await self.redis.hgetall(f'reaction_roles:{message_id}')
            ).items()
        }

    async def delete(self, message_id: int) -> None:
        await self.redis.delete(f'reaction_roles:{message_id}')
