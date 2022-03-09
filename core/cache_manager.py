from __future__ import annotations

from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from aioredis import Redis

__all__ = ('DeleteMessageManager',)

class DeleteMessageManager:
    __slots__ = ('redis',)

    def __init__(self, redis: Redis) -> None:
        self.redis = redis
    
    async def get_messages(self, message_id: int, one_only: bool) -> List[int]:
        return await self.redis.lrange(f'delete_messages:{message_id}', 0, 0 if one_only else -1)
    
    async def add_message(self, message_id: int, message_maybe_delete: int) -> int:
        return await self.redis.lpush(f'delete_messages:{message_id}', message_maybe_delete)
    
    async def remove_message(self, message_id: int, message_maybe_delete: int) -> None:
        await self.redis.lrem(f'delete_messages:{message_id}', 0, message_maybe_delete)    
