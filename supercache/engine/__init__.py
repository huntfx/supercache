"""The engine is a class that directly controls the cache.

It must have these methods:
    get(key): Get an item of cache
    put(key, value, **kwargs): Set an item of cache

It may optionally have these methods:
    __iter__(): Iterate through all keys
    delete(key): Remove an item of cache
    exists(key): If a key exists
    hits(key): How many cache hits have happened
    misses(key): How many cache misses have happened
"""

from .memcached import Memcached
from .memory import Memory
from .sqlite import SQLite
