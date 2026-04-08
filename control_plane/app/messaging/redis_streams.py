import json

import redis

from control_plane.app.core.config import settings


class RedisStreamsBus:
    def __init__(self) -> None:
        self.client = redis.Redis.from_url(settings.redis_url, decode_responses=True)

    def publish(self, stream: str, key: str, payload: dict) -> str:
        return self.client.xadd(stream, {"key": key, "payload": json.dumps(payload)})

    def ensure_group(self, stream: str, group: str) -> None:
        try:
            self.client.xgroup_create(stream, group, id="0", mkstream=True)
        except redis.ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise

    def consume(self, stream: str, group: str, consumer: str, count: int = 10, block_ms: int = 1000) -> list[tuple]:
        self.ensure_group(stream, group)
        return self.client.xreadgroup(group, consumer, {stream: ">"}, count=count, block=block_ms)

    def ack(self, stream: str, group: str, message_id: str) -> None:
        self.client.xack(stream, group, message_id)
