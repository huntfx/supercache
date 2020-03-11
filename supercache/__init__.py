import inspect
import os
import sys
import time
from functools import partial, wraps

from .fingerprint import fingerprint
from .utils import *
from .backend import *


__version__ = '1.2.0'

_slots = []


class Memoize(object):
    """Base cache wrapper.
    This is designed to be added to a function as a decorator.

    Example:
        @cache(timeout=60)
        def func(): pass
    """

    __slots__ = [
        'cache_data', 'cache_accessed', 'cache_size', 'cache_order', 'cache_hits', 'cache_misses',
        'keys', 'ignore', 'timeout', 'size', 'precalculate',
    ]

    def __init__(self, keys=None, ignore=None, timeout=None, size=None, precalculate=False):
        """Define the caching options.

        The cache key is generated from a function and its arguments,
        with the option to ignore certain parameters if they don't
        affect the output.

        Take a function "format_data", that has the parameters
        "print_messages" and "json_convert". No matter if printing
        or not, the output won't change, so we can ignore this.
        However, the value of "json_convert" will change the output,
        so that needs to be included in the cache.

        keys (list):
            Arguments or keywords to include in the cache.
            May contain int, str, slice or regex.
        ignore (list):
            Arguments or keywords in ignore from the cache.
            May contain int, str, slice or regex.
        timeout (int):
            How many seconds the cache is valid for.
            Set to None for infinite.
        size (int):
            Maximum size of cache in bytes.
            Set to None for infinite.
        precalculate (bool):
            Convert a generator to a tuple.
        """

        self.keys = keys
        self.ignore = ignore
        self.timeout = timeout
        self.size = size
        self.precalculate = precalculate

    def __call__(self, fn):
        """Setup function cache."""

        @wraps(fn)
        def wrapper(*args, **kwargs):

            try:
                f = partial(fn, *args, **kwargs)
            except TypeError:
                if isinstance(fn, (classmethod, staticmethod, property)):
                    raise TypeError("unhashable type '{}'".format(fn.__class__.__name__))
                raise

            uid = fingerprint(f, keys=self.keys, ignore=self.ignore)

            # Only read the time if timeouts are set
            # Not a huge cost save, but every little helps
            if self.timeout is not None:
                current_time = time.time()

            # Determine if the function needs to be run (again)
            cache_exists = uid in self.cache_data
            if (not cache_exists
                or (self.timeout is not None
                    and current_time - self.timeout > self.cache_accessed.get(uid, current_time))):

                # Execute the actual function
                self.cache_misses[uid] += 1
                if inspect.isgeneratorfunction(fn):
                    if self.precalculate:
                        self.cache_data[uid] = tuple(f())
                    else:
                        self.cache_data[uid] = GeneratorCache(f)
                else:
                    self.cache_data[uid] = f()

                if self.timeout is not None:
                    self.cache_accessed[uid] = current_time

                # Deal with the cache size limit
                if self.size is not None:

                    # Mark down the order at which cache was added
                    if cache_exists:
                        self.cache_order.remove(uid)
                    self.cache_order.append(uid)

                    # Calculate the size of the object
                    self.cache_size[uid] = getsize(self.cache_data[uid])
                    self.cache_size[None] += self.cache_size[uid]

                    # Remove old cache until under the size limit
                    while self.cache_size[None] > self.size:
                        cache_id = self.cache_order.pop(0)

                        # Emergency stop if it's the final item
                        if cache_id == uid:
                            self.cache_order.append(uid)
                            if self.cache_order[1:]:
                                continue
                            else:
                                break

                        del self.cache_data[cache_id]
                        if self.timeout is not None:
                            del self.cache_accessed[cache_id]
                        self.cache_size[None] -= self.cache_size.pop(cache_id)
            else:
                self.cache_hits[uid] += 1

            return self.cache_data[uid]
        return wrapper


class Cache(object):
    def __init__(self, group=None, type=DictCache):
        self.group = group
        self.type = type
        self.data = self.type.data[self.group]

    def __call__(self, *args, **kwargs):
        """Create a new memoize instance."""

        new = Memoize(*args, **kwargs)
        new.cache_data = self.data[self.type.Result]
        new.cache_accessed = self.data[self.type.Accessed]
        new.cache_size = self.data[self.type.Size]
        new.cache_order = self.data[self.type.Order]
        new.cache_hits = self.data[self.type.Hits]
        new.cache_misses = self.data[self.type.Misses]
        return new

    def _delete_uid(self, uid):
        """Remove a single cache record."""

        try:
            del self.data[self.type.Result][uid]
        except KeyError:
            pass
        else:
            if uid in self.data[self.type.Accessed]:
                del self.data[self.type.Accessed][uid]
            if uid in self.data[self.type.Size]:
                del self.data[self.type.Size][uid]
                self.data[self.type.Order].remove(uid)
            if uid in self.data[self.type.Hits]:
                del self.data[self.type.Hits][uid]
            if uid in self.data[self.type.Misses]:
                del self.data[self.type.Misses][uid]

    def delete(self, fn=None, *args, **kwargs):
        """Delete cache for a function.
        If no arguments are given, all instances will be cleared.
        Give arguments to only delete a specific cache value.
        """

        # Reset all the cache in place
        if fn is None:
            defaults = self.type.defaults()
            self.data[self.type.Result].clear()
            self.data[self.type.Result].update(defaults[self.type.Result])
            self.data[self.type.Accessed].clear()
            self.data[self.type.Accessed].update(defaults[self.type.Accessed])
            self.data[self.type.Size].clear()
            self.data[self.type.Size].update(defaults[self.type.Size])
            self.data[self.type.Order][:] = defaults[self.type.Order]
            self.data[self.type.Hits].clear()
            self.data[self.type.Hits].update(defaults[self.type.Hits])
            self.data[self.type.Misses].clear()
            self.data[self.type.Misses].update(defaults[self.type.Misses])

        # Remove cache for specific execution
        elif args or kwargs:
            self._delete_uid(fingerprint(partial(extract_decorated_func(fn), *args, **kwargs)))

        # Remove all cache under a function
        else:
            func_hash = hash(extract_decorated_func(fn))
            for key in {k for k in self.data[self.type.Result].keys() if k[0] == func_hash}:
                self._delete_uid(key)

    def _count(self, dct, fn=None, *args, **kwargs):
        """Count a number of occurances."""

        # Count all records
        if fn is None:
            return sum(dct.values())

        func = extract_decorated_func(fn)

        # Count records for a particular function with arguments
        if args or kwargs:
            return dct.get(fingerprint(partial(func, *args, **kwargs)), 0)

        # Count records for a particular function
        func_hash = hash(func)
        return sum(v for k, v in dct.items() if k[0] == func_hash)

    def hits(self, fn=None, *args, **kwargs):
        """Count the number of times the cache has been used."""

        return self._count(self.data[self.type.Hits], fn, *args, **kwargs)

    def misses(self, fn=None, *args, **kwargs):
        """Count the number of times the cache has been regenerated."""

        return self._count(self.data[self.type.Misses], fn, *args, **kwargs)

    def exists(self, fn=None, *args, **kwargs):
        """Find if cache exists for a certain input."""

        # If any cache exists
        if fn is None:
            return bool(self.data[self.type.Result])

        func = extract_decorated_func(fn)

        # Cache exists for a particular function with arguments
        if args or kwargs:
            return fingerprint(partial(func, *args, **kwargs)) in self.data[self.type.Result]

        # Cache exists for a particular function
        func_hash = hash(func)
        for key in self.data[self.type.Result]:
            if key[0] == func_hash:
                return True
        return False


# Setup default cache group
cache = Cache(None)
