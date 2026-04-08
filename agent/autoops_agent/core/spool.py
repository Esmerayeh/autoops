from ..storage.sqlite_spool import SQLiteSpool
from .config import settings


def get_spool() -> SQLiteSpool:
    return SQLiteSpool(settings.spool_path)
