import sqlite3
from collections import Iterable


class Database(object):
    """Database wrapper."""

    def __init__(self, path, debug=False):
        # type: (str) -> None
        self.path = path
        self.conn = sqlite3.connect(path)
        self.cursor = self.conn.cursor()
        self.debug = debug

    @staticmethod
    def sanitize(s):
        # type: (str) -> str
        return '"{}"'.format(s.replace("'", "''").replace('"', '""'))

    @staticmethod
    def desanitize(s):
        # type: (str) -> str
        return s.replace("''", "'").replace('""', '"').strip('"')

    def table_exists(self, table_name):
        # type: (str) -> bool
        query = 'SELECT COUNT(*) FROM sqlite_master WHERE type="table" AND name=?'
        return self.cursor.execute(query, [Database.desanitize(table_name)]).fetchone()[0] > 0

    def result_exists(self):
        return self.cursor.fetchone() is not None

    def commit(self):
        # type: () -> None
        self.conn.commit()

    def hard_close(self):
        # type: () -> None
        self.conn.close()

    def close(self):
        # type: () -> None
        self.commit()
        self.hard_close()

    def __enter__(self):
        # type: () -> Database
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # type: () -> None
        self.close()