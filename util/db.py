import sqlite3
import threading


class Database(object):
    """Database wrapper."""

    def __init__(self, path, debug=False):
        # type: (str) -> None
        self.path = path
        self.conn = sqlite3.connect(path, check_same_thread=False)
        # mulithreading is only safe when Database.lock() is used
        self.cursor = self.conn.cursor()
        self._lock = threading.RLock()
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

    def lock(self):
        # type: () -> None
        self._lock.acquire()

    def release_lock(self):
        # type: () -> None
        self._lock.release()

    def __enter__(self):
        # type: () -> Database
        self.lock()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # type: () -> None
        self.release_lock()

    def reset_connection(self):
        self.conn = sqlite3.connect(self.path)
        self.cursor = self.conn.cursor()
