import time
from collections import defaultdict

from . import exceptions, utils


class Memory(object):
    """Memory based caching."""

    FIFO = FirstInFirstOut = 0
    FILO = FirstInLastOut = 1
    LRU = LeastRecentlyUsed = 2
    MRU = MostRecentlyUsed = 3
    LFU = LeastFrequentlyUsed = 4

    def __init__(self, mode=LRU, ttl=None, count=None, size=None):
        """Create a new engine.

        Parameters:
            mode (int): How to purge the old keys.
            ttl (int): Time the cache is valid for.
                Set to None for infinite.
            count (int): Maximum cache results to store.
                Set to None for infinite.
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
        self.purge()
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
        return self.data['ttl'][key] <= _current_time

    def get(self, key, purge=False):
        """Get the value belonging to a key.
        An error will be raised if the cache is expired or doesn't
        exist.
        """
        if purge:
            self.purge()

        if not self.exists(key):
            raise exceptions.CacheNotFound(key)

        # If a purge was done, then skip the expiry check
        if not purge and self.expired(key):
            raise exceptions.CacheExpired(key)

        self.data['hits'][key] += 1
        self.data['access'][key] = time.time()

        return self.data['result'][key]

    def put(self, key, value, ttl=None, purge=True):
        """Add a new value to cache.
        This will overwrite any old cache with the same key.
        """
        self.data['result'][key] = value
        self.data['misses'][key] += 1

        # Calculate size
        if self.size is not None:
            size = utils.getsize(value)
            self.data['size'][None] += size - self.data['size'].get(key, 0)
            self.data['size'][key] = size

        # Set insert/access time
        current_time = time.time()
        self.data['insert'][key] = self.data['access'][key] = current_time

        # Set timeout
        if ttl is None and self.ttl is None:
            if key in self.data['ttl']:
                del self.data['ttl'][key]
        else:
            if ttl is None:
                ttl = self.ttl
            self.data['ttl'][key] = current_time + ttl
            self._next_ttl = min(self._next_ttl, self.data['ttl'][key])

        # Clean old keys
        if purge:
            self.purge(ignore=key)

    def delete(self, key):
        """Delete an item of cache.
        This will not remove the hits, misses or ttl.
        """
        if key in self.data['result']:
            del self.data['result'][key]
            del self.data['insert'][key]
            del self.data['access'][key]
            if self.size is not None:
                self.data['size'][None] -= self.data['size'].pop(key)
            return True
        return False

    def purge(self, ignore=None):
        """Remove old cache."""
        count = self.count
        size = self.size
        purged = []

        # Check timeouts
        if self.data['ttl']:
            current_time = time.time()
            if current_time > self._next_ttl:
                self._next_ttl = float('inf')
                for key in tuple(self.data['result']):
                    if self.expired(key, _current_time=current_time):
                        self.delete(key)
                    elif key in self.data['ttl']:
                        self._next_ttl = min(self._next_ttl, self.data['ttl'][key])

        # Determine if we can skip
        if self.count is not None and len(self.data['result']) < self.count:
            count = None
        if self.size is not None and self.data['size'][None] < self.size:
            size = None

        if count is None and size is None:
            return purged

        # Order the keys
        if self.mode == self.FirstInFirstOut:
            sort_key = lambda k: self.data['insert'][k]
        elif self.mode == self.FirstInLastOut:
            sort_key = lambda k: -self.data['insert'][k]
        elif self.mode == self.LeastRecentlyUsed:
            sort_key = lambda k: self.data['access'][k]
        elif self.mode == self.MostRecentlyUsed:
            sort_key = lambda k: -self.data['access'][k]
        elif self.mode == self.LeastFrequentlyUsed:
            sort_key = lambda k: self.data['hits'][k]
        else:
            raise NotImplementedError(self.mode)
        ordered_keys = sorted(self.data['result'], key=sort_key, reverse=True)

        # Remove the cache data
        if self.count is not None:
            for key in ordered_keys[self.count:]:
                if key == ignore:
                    continue
                self.delete(key)
                purged.append(key)

        if self.size is not None:
            total_size = 0
            for key in ordered_keys:
                if key == ignore:
                    continue
                total_size += self.data['size'][key]
                if total_size > self.size:
                    self.delete(key)
                    purged.append(key)

        return purged

    def hits(self, key):
        """Return the number of hits on an item of cache."""
        return self.data['hits'].get(key, 0)

    def misses(self, key):
        """Return the number of misses on an item of cache."""
        return self.data['misses'].get(key, 0)
