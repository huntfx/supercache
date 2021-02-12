import time
from collections import defaultdict

from .. import exceptions, utils


class Memory(object):
    """Cache directly in memory.
    This is by far the fastest solution, but the cache cannot be shared
    outside the current process.
    This is not completely thread safe, but care has been taken to
    avoid any errors from stopping the code working.
    """

    FIFO = FirstInFirstOut = 0
    FILO = FirstInLastOut = 1
    LRU = LeastRecentlyUsed = 2
    MRU = MostRecentlyUsed = 3
    LFU = LeastFrequentlyUsed = 4

    def __init__(self, ttl=None, mode=LRU, count=None, size=None):
        """Create a new engine.

        Parameters:
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
        self.data = dict(
            result={},
            hits=defaultdict(int),
            misses=defaultdict(int),
            size={None: 0},
            ttl={},
            insert={},
            access={}
        )

        self.mode = mode
        self.ttl = ttl
        self.count = count
        self.size = size

        self._next_ttl = float('inf')

    def keys(self):
        """Get the current stored cache keys."""
        return list(iter(self))

    def __iter__(self):
        """Iterate through all the keys."""
        self._purge()
        return iter(self.data['result'])

    def exists(self, key):
        """Find if cache currently exists for a given key.
        Any key past its ttl will be removed.
        """
        if key in self.data['result']:
            if self.expired(key):
                self.delete(key)
                return False
            return True
        return False

    def expired(self, key, _current_time=None):
        """Determine is a key has expired."""
        if key not in self.data['ttl']:
            return False
        if _current_time is None:
            _current_time = time.time()
        try:
            return self.data['ttl'][key] <= _current_time
        except KeyError:
            return True

    def get(self, key, purge=False):
        """Get the value belonging to a key.
        An error will be raised if the cache is expired or doesn't
        exist.
        """
        if purge:
            self._purge()

        if not self.exists(key):
            raise exceptions.CacheNotFound(key)

        # If a purge was done, then skip the expiry check
        if not purge and self.expired(key):
            raise exceptions.CacheExpired(key)

        try:
            self.data['hits'][key] += 1
            self.data['access'][key] = time.time()

            return self.data['result'][key]
        except KeyError:
            raise exceptions.CacheExpired(key)

    def put(self, key, value, ttl=None, purge=True):
        """Add a new value to cache.
        This will overwrite any old cache with the same key.
        """
        if ttl is None:
            ttl = self.ttl

        self.data['result'][key] = value
        try:
            self.data['misses'][key] += 1
        except KeyError:
            self.data['misses'][key] = 1

        # Calculate size
        if self.size is not None:
            size = utils.getsize(value)
            self.data['size'][None] += size - self.data['size'].get(key, 0)
            self.data['size'][key] = size

        # Set insert/access time
        current_time = time.time()
        self.data['insert'][key] = self.data['access'][key] = current_time

        # Set timeout
        if ttl is None or ttl <= 0:
            try:
                del self.data['ttl'][key]
            except KeyError:
                pass
        else:
            self.data['ttl'][key] = current_time + ttl
            self._next_ttl = min(self._next_ttl, self.data['ttl'][key])

        # Clean old keys
        if purge:
            self._purge(ignore=key)

    def delete(self, key):
        """Delete an item of cache.
        This will not remove the hits or misses.
        """
        if key in self.data['result']:
            try:
                del self.data['result'][key]
                del self.data['insert'][key]
                del self.data['access'][key]
                if key in self.data['ttl']:
                    del self.data['ttl'][key]
                if self.size is not None:
                    self.data['size'][None] -= self.data['size'].pop(key)
            except KeyError:
                pass
            return True
        return False

    def hits(self, key):
        """Return the number of hits on an item of cache."""
        return self.data['hits'].get(key, 0)

    def misses(self, key):
        """Return the number of misses on an item of cache."""
        return self.data['misses'].get(key, 0)

    def _purge(self, ignore=None):
        """Remove old cache."""
        count = self.count
        size = self.size
        purged = 0

        # Delete expired
        if self.data['ttl']:
            current_time = time.time()
            if current_time > self._next_ttl:
                self._next_ttl = float('inf')
                for key in tuple(self.data['result']):
                    if self.expired(key, _current_time=current_time):
                        self.delete(key)
                    elif key in self.data['ttl']:
                        try:
                            self._next_ttl = min(self._next_ttl, self.data['ttl'][key])
                        except KeyError:
                            pass

        # Determine if we can skip
        if count is not None and len(self.data['result']) < count:
            count = None
        if size is not None and self.data['size'][None] < size:
            size = None

        if count is None and size is None:
            return purged

        # Order the keys
        if self.mode == self.FirstInFirstOut:
            order_by = lambda k: self.data['insert'][k]
        elif self.mode == self.FirstInLastOut:
            order_by = lambda k: -self.data['insert'][k]
        elif self.mode == self.LeastRecentlyUsed:
            order_by = lambda k: self.data['access'][k]
        elif self.mode == self.MostRecentlyUsed:
            order_by = lambda k: -self.data['access'][k]
        elif self.mode == self.LeastFrequentlyUsed:
            order_by = lambda k: self.data['hits'][k]
        else:
            raise NotImplementedError(self.mode)
        ordered_keys = sorted(self.data['result'], key=order_by, reverse=True)

        # Remove the cache data
        if count is not None:
            for key in ordered_keys[count:]:
                if key == ignore:
                    continue
                self.delete(key)
                purged += 1
        if size is not None:
            total_size = 0
            for key in ordered_keys:
                if key == ignore:
                    continue
                total_size += self.data['size'][key]
                if total_size > size:
                    self.delete(key)
                    purged += 1
        return purged
