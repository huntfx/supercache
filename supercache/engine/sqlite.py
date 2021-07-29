import base64
import pickle
import sqlite3
import sys
import time

from .. import exceptions, utils


def _encode(value):
    """Encode any Python object."""
    return base64.b64encode(pickle.dumps(value))


def _decode(value):
    """Decode any Python object."""
    return pickle.loads(base64.b64decode(value))


class SQLite(object):
    """Local database caching.
    This is slower than the local memory based caching, but has the
    advantage of being persistent. This should be used if the cache is
    to be shared across multiple processes on the same machine.
    """

    FIFO = FirstInFirstOut = 0
    FILO = FirstInLastOut = 1
    LRU = LeastRecentlyUsed = 2
    MRU = MostRecentlyUsed = 3
    LFU = LeastFrequentlyUsed = 4

    def __init__(self, database=':memory:', mode=LRU, ttl=None, count=None, size=None):
        """Create a new engine.

        Parameters:
            data (str): Path to the database.
            mode (int): How to purge the old keys.
            ttl (int): Time the cache is valid for.
                Set to None for infinite.
            count (int): Maximum cache results to store.
                Set to None or 0 for infinite.
            size (int): Maximum size of cache in bytes.
                This is a soft limit, where the memory will be
                allocated first, and any extra cache purged later.
                The latest cache item will always be stored.
                Set to None for infinite.
        """
        self.connection = sqlite3.connect(database)
        cursor = self.connection.cursor()

        # Create tables on first run
        cursor.execute(
            'CREATE TABLE IF NOT EXISTS data ('
                'key PRIMARY KEY,'
                'value NULL,'
                'encoded DEFAULT false,'
                'ttl NULL,'
                'size NULL,'
                'inserted NOT NULL,'
                'accessed NOT NULL'
            ')'
        )
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_ttl ON data (ttl)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_size ON data (size)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_ins ON data (inserted)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_access ON data (accessed)')
        cursor.execute(
            'CREATE TABLE IF NOT EXISTS stats ('
                'key PRIMARY KEY,'
                'hits DEFAULT 0,'
                'misses DEFAULT 0'
            ')'
        )

        self.mode = mode
        self.ttl = ttl
        self.count = count
        self.size = size

        # Don't allow cross version caches
        # Pickle may have incompatibilities between versions
        self._key_prefix = '{}.{}.'.format(sys.version_info.major, sys.version_info.minor)

    def keys(self):
        """Get the current stored cache keys."""
        return list(iter(self))

    def __iter__(self, _cursor=None):
        """Iterate through all the keys."""
        cursor = _cursor or self.connection.cursor()

        self._purge()
        prefix_len = len(self._key_prefix)
        cursor.execute('SELECT key FROM data')
        for key, in cursor.fetchall():
            yield key[prefix_len:]

    def exists(self, key, _cursor=None):
        """Find if cache currently exists for a given key.
        Any key past its ttl will be removed.
        """
        key = self._key_prefix + key
        cursor = _cursor or self.connection.cursor()

        # Determine if the key exists
        cursor.execute('SELECT ttl FROM data WHERE key = ?', (key,))
        result = cursor.fetchone()
        if result is None:
            return False

        # Check the ttl
        ttl, = result
        if ttl is not None and ttl < time.time():
            self.delete(key)
            return False
        return True

    def expired(self, key, _cursor=None):
        """Determine is a key has expired."""
        key = self._key_prefix + key
        cursor = _cursor or self.connection.cursor()

        cursor.execute('SELECT ttl FROM data WHERE key = ?', (key,))
        try:
            ttl, = cursor.fetchone()
        except TypeError:
            raise exceptions.CacheNotFound(key)
        return ttl is not None and ttl < time.time()

    def get(self, key, purge=False, _cursor=None):
        """Get the value belonging to a key.
        An error will be raised if the cache is expired or doesn't
        exist.
        """
        key = self._key_prefix + key
        cursor = _cursor or self.connection.cursor()

        if purge:
            self._purge(_cursor=cursor)

        # Attempt to get data
        cursor.execute('SELECT value, encoded, ttl FROM data WHERE key = ?', (key,))
        try:
            value, encoded, ttl = cursor.fetchone()
        except TypeError:
            raise exceptions.CacheNotFound(key)

        # If a purge was done, then skip the expiry check
        if not purge and ttl is not None and ttl <= time.time():
            raise exceptions.CacheExpired(key)

        # Update stats
        cursor.execute('UPDATE data SET accessed = ? WHERE key = ?', (time.time(), key))
        cursor.execute('UPDATE stats SET hits = hits + 1 WHERE key = ?', (key,))
        self.connection.commit()

        if encoded:
            return _decode(value)
        return value

    def put(self, key, value, ttl=None, purge=True, _cursor=None):
        """Write a new value to the cache.
        This will overwrite any old cache with the same key.
        """
        key = self._key_prefix + key
        cursor = _cursor or self.connection.cursor()

        if ttl is None:
            ttl = self.ttl

        # Generate query parameters
        current_time = time.time()
        data = dict(key=key, inserted=current_time, accessed=current_time)

        # Calculate TTL
        if ttl is None or ttl <= 0:
            data['ttl'] = None
        else:
            data['ttl'] = current_time + ttl

        # Encode the value if required
        try:
            raw_types = (bool, str, int, float, type(None), bytes)
        except NameError:
            raw_types = (bool, str, int, float, type(None), unicode)
        if isinstance(value, raw_types) and not (isinstance(value, int) and value >= 2**63):
            data['value'] = value
            data['encoded'] = False
        else:
            data['value'] = _encode(value)
            data['encoded'] = True

        # Only calculate size if it's being tracked
        if self.size is not None:
            size = utils.getsize(data['value'])
            data['size'] = size

        # Insert/update data
        keys, values = zip(*data.items())
        cursor.execute(
            'UPDATE data SET {} WHERE key = ?'.format(
                ', '.join(key + ' = ?' for key in keys)
            ), values + (key,),
        )
        if not cursor.rowcount:
            cursor.execute(
                'INSERT INTO data ({}) VALUES ({})'.format(
                    ', '.join(keys),
                    ', '.join('?' for _ in keys)
                ), values,
            )

        # Update stats
        cursor.execute('UPDATE stats SET misses = misses + 1 WHERE key = ?', (key,))
        if not cursor.rowcount:
            cursor.execute('INSERT INTO stats (key, misses) VALUES (?, 1)', (key,))
        self.connection.commit()

        # Clean old keys
        if purge:
            self._purge(ignore=key, _cursor=cursor)

    def delete(self, key, _cursor=None):
        """Delete an item of cache if it exists.
        This will not remove the hits or misses.
        """
        key = self._key_prefix + key
        cursor = _cursor or self.connection.cursor()

        cursor.execute('DELETE FROM data WHERE key = ?', (key,))
        self.connection.commit()
        return bool(cursor.rowcount)

    def hits(self, key, _cursor=None):
        """Return the number of hits on an item of cache."""
        key = self._key_prefix + key
        cursor = _cursor or self.connection.cursor()

        cursor.execute('SELECT hits FROM stats WHERE key = ?', (key,))
        try:
            return cursor.fetchone()[0]
        except TypeError:
            return 0

    def misses(self, key, _cursor=None):
        """Return the number of misses on an item of cache."""
        key = self._key_prefix + key
        cursor = _cursor or self.connection.cursor()

        cursor.execute('SELECT misses FROM stats WHERE key = ?', (key,))
        try:
            return cursor.fetchone()[0]
        except TypeError:
            return 0

    def _purge(self, ignore=None, _cursor=None):
        """Remove old cache."""
        cursor = _cursor or self.connection.cursor()

        count = self.count
        size = self.size
        purged = 0

        # Delete expired
        cursor.execute('DELETE FROM data WHERE ttl IS NOT NULL AND ttl < ?', (time.time(),))
        purged += cursor.rowcount

        # Determine if we can skip
        if size is not None:
            cursor.execute('SELECT SUM(size) FROM data')
            total, = cursor.fetchone()
            if total is None or total <= size:
                size = None
        if count is None and size is None:
            return

        # Setup the order by query
        if self.mode == self.FirstInFirstOut:
            order_by = 'inserted DESC'
        elif self.mode == self.FirstInLastOut:
            order_by = 'inserted ASC'
        elif self.mode == self.LeastRecentlyUsed:
            order_by = 'accessed DESC'
        elif self.mode == self.MostRecentlyUsed:
            order_by = 'accessed ASC'
        elif self.mode == self.LeastFrequentlyUsed:
            order_by = '(SELECT hits FROM stats WHERE stats.key == data.key) DESC'
        else:
            raise NotImplementedError(self.mode)

        # Remove any rows above a certain count
        if count is not None:
            cursor.execute(
                'DELETE FROM data WHERE key NOT IN ('
                    'SELECT key FROM data WHERE key != ? ORDER BY {} LIMIT ?'
                ')'.format(order_by), (ignore, count)
            )
            purged += cursor.rowcount

        # Remove rows until the total size is under a certain amount
        # This could probably be optimised
        if size is not None:
            # Flip the direction
            order_by, direction = order_by.rsplit(' ', 1)
            if direction == 'DESC':
                order_by += ' ASC'
            else:
                order_by += ' DESC'

            remove = []
            cursor.execute(
                'SELECT key, size FROM data WHERE key != ? ORDER BY {}'.format(order_by), (ignore,),
            )
            for i, (key, cache_size) in enumerate(cursor.fetchall()):
                remove.append(key)
                total -= cache_size
                if total <= size:
                    break

            # Delete the keys
            cursor.execute(
                'DELETE FROM data WHERE key IN ({})'.format(
                    ', '.join('?' for _ in remove),
                ), remove,
            )
            purged += cursor.rowcount

        if purged:
            self.connection.commit()
        return purged
