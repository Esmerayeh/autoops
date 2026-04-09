import json
import sqlite3
from pathlib import Path


class SQLiteStreamsBus:
    def __init__(self, url: str) -> None:
        prefix = "sqlite:///"
        raw_path = url[len(prefix) :] if url.startswith(prefix) else url
        self.path = Path(raw_path).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        connection.execute("pragma journal_mode=WAL")
        connection.execute("pragma synchronous=NORMAL")
        return connection

    def _ensure_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                create table if not exists stream_messages (
                    id integer primary key autoincrement,
                    stream text not null,
                    message_key text not null,
                    payload text not null,
                    created_at text not null default current_timestamp
                )
                """
            )
            connection.execute(
                """
                create table if not exists stream_acks (
                    stream text not null,
                    group_name text not null,
                    message_id integer not null,
                    acked_at text not null default current_timestamp,
                    primary key (stream, group_name, message_id)
                )
                """
            )

    def publish(self, stream: str, key: str, payload: dict) -> str:
        with self._connect() as connection:
            cursor = connection.execute(
                "insert into stream_messages(stream, message_key, payload) values (?, ?, ?)",
                (stream, key, json.dumps(payload)),
            )
            return str(cursor.lastrowid)

    def ensure_group(self, stream: str, group: str) -> None:
        return None

    def consume(self, stream: str, group: str, consumer: str, count: int = 10, block_ms: int = 1000) -> list[tuple]:
        del consumer, block_ms
        with self._connect() as connection:
            rows = connection.execute(
                """
                select id, message_key, payload
                from stream_messages
                where stream = ?
                  and id not in (
                    select message_id from stream_acks where stream = ? and group_name = ?
                  )
                order by id asc
                limit ?
                """,
                (stream, stream, group, count),
            ).fetchall()
        if not rows:
            return []
        messages = [(str(message_id), {"key": key, "payload": payload}) for message_id, key, payload in rows]
        return [(stream, messages)]

    def ack(self, stream: str, group: str, message_id: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "insert or ignore into stream_acks(stream, group_name, message_id) values (?, ?, ?)",
                (stream, group, int(message_id)),
            )
