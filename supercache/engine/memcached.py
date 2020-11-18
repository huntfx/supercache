import pickle
import sys

from .. import exceptions


def _encode(value):
    """Convert a Python object to work with memcached."""
    return pickle.dumps(value)


def _decode(value):
    """Convert a memcached string back to a Python object."""
    return pickle.loads(value)


class Memcached(object):
    """Memcached based caching.
    This is extremely lightweight in terms of memory usage, but it
    appears to be slightly slower than local database caching, and a
    lot slower than local memory based caching. This should be used if
    the cache is to be shared between multiple users.
    """

    LRU = LeastRecentlyUsed = 0

    def __init__(self, url='127.0.0.1', mode=LRU, ttl=None):
        """Create a new engine.

        Parameters:
            url (str): Memcached server to connect to.
            mode (int): How to purge the old keys.
                This does not affect anything as memcached is LRU only.
                The option is there to match the other engines.
            ttl (int): Time the cache is valid for.
                Set to None or 0 for infinite.
        """
        try:
            from pymemcache.client.base import Client
            self.client = Client(url, timeout=3, connect_timeout=3)
        except ImportError:
            from memcache import Client
            self.client = Client([url], socket_timeout=3)
        self.ttl = ttl

        # Don't allow cross version caches
        # Pickle may have incompatibilities between versions
        self._key_prefix = '{}.{}.'.format(sys.version_info.major, sys.version_info.minor)

    def get(self, key):
        """Get the value belonging to a key.
        An error will be raised if the cache is expired or doesn't
        exist.
        """
        value = self.client.get(self._key_prefix + key)
        if value is None:
            raise exceptions.CacheNotFound(key)
        return _decode(value)

    def put(self, key, value, ttl=None):
        """Write a new value to the cache.
        This will overwrite any old cache with the same key.
        """
        if ttl is None:
            ttl = self.ttl
        self.client.set(self._key_prefix + key, _encode(value), ttl or 0, noreply=True)

    def delete(self, key):
        """Delete an item of cache if it exists."""
        return self.client.delete(self._key_prefix + key, noreply=False)
