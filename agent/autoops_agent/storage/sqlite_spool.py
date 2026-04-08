import json
import sqlite3
from pathlib import Path


class SQLiteSpool:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.conn = sqlite3.connect(self.path)
        self.conn.execute(
            "create table if not exists spool (id integer primary key autoincrement, event_type text, payload text, created_at text)"
        )

    def append(self, event_type: str, payload: dict) -> None:
        self.conn.execute(
            "insert into spool(event_type, payload, created_at) values (?, ?, datetime('now'))",
            (event_type, json.dumps(payload)),
        )
        self.conn.commit()

    def fetch_batch(self, limit: int = 100) -> list[tuple]:
        return list(self.conn.execute("select id, event_type, payload from spool order by id asc limit ?", (limit,)))

    def ack(self, ids: list[int]) -> None:
        if not ids:
            return
        placeholders = ",".join("?" for _ in ids)
        self.conn.execute(f"delete from spool where id in ({placeholders})", ids)
        self.conn.commit()
