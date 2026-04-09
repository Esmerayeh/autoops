import json

import redis

from control_plane.app.core.config import settings
from control_plane.app.messaging.sqlite_streams import SQLiteStreamsBus


class RedisStreamsBus:
    def __init__(self) -> None:
        stream_url = settings.stream_url
        if stream_url.startswith("sqlite:///"):
            self.backend = SQLiteStreamsBus(stream_url)
            self.client = None
        else:
            self.backend = None
            self.client = redis.Redis.from_url(stream_url or settings.redis_url, decode_responses=True)

    def publish(self, stream: str, key: str, payload: dict) -> str:
        if self.backend:
            return self.backend.publish(stream, key, payload)
        return self.client.xadd(stream, {"key": key, "payload": json.dumps(payload)})

    def ensure_group(self, stream: str, group: str) -> None:
        if self.backend:
            self.backend.ensure_group(stream, group)
            return
        try:
            self.client.xgroup_create(stream, group, id="0", mkstream=True)
        except redis.ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise

    def consume(self, stream: str, group: str, consumer: str, count: int = 10, block_ms: int = 1000) -> list[tuple]:
        if self.backend:
            return self.backend.consume(stream, group, consumer, count=count, block_ms=block_ms)
        self.ensure_group(stream, group)
        return self.client.xreadgroup(group, consumer, {stream: ">"}, count=count, block=block_ms)

    def ack(self, stream: str, group: str, message_id: str) -> None:
        if self.backend:
            self.backend.ack(stream, group, message_id)
            return
        self.client.xack(stream, group, message_id)
