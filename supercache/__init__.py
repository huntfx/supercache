import inspect
import os
import sys
import time
from collections import defaultdict
from functools import partial, wraps

from .fingerprint import fingerprint
from .utils import *


__version__ = '1.0.0'


class cache(object):
    """Base cache wrapper.
    This is designed to be added to a function as a decorator.

    Example:
        @cache(timeout=60)
        def func(): pass
    """

    Data = {}
    Accessed = {}
    Size = {None: 0}
    Order = []
    Hits = defaultdict(int)
    Misses = defaultdict(int)

    __slots__ = ['keys', 'ignore', 'timeout', 'size', 'precalculate']

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
            cache_exists = uid in self.Data
            if (not cache_exists
                or (self.timeout is not None
                    and current_time - self.timeout > self.Accessed.get(uid, current_time))):

                # Execute the actual function
                self.Misses[uid] += 1
                if inspect.isgeneratorfunction(fn):
                    if self.precalculate:
                        self.Data[uid] = tuple(f())
                    else:
                        self.Data[uid] = GeneratorCache(f)
                else:
                    self.Data[uid] = f()

                if self.timeout is not None:
                    self.Accessed[uid] = current_time

                # Deal with the cache size limit
                if self.size is not None:

                    # Mark down the order at which cache was added
                    if cache_exists:
                        self.Order.remove(uid)
                    self.Order.append(uid)

                    # Calculate the size of the object
                    self.Size[uid] = getsize(self.Data[uid])
                    self.Size[None] += self.Size[uid]

                    # Remove old cache until under the size limit
                    while self.Size[None] > self.size:
                        cache_id = self.Order.pop(0)

                        # Emergency stop if it's the final item
                        if cache_id == uid:
                            self.Order.append(uid)
                            if self.Order[1:]:
                                continue
                            else:
                                break

                        del self.Data[cache_id]
                        if self.timeout is not None:
                            del self.Accessed[cache_id]
                        self.Size[None] -= self.Size.pop(cache_id)
            else:
                self.Hits[uid] += 1

            return self.Data[uid]
        return wrapper

    @classmethod
    def _delete_uid(cls, uid):
        """Remove a single cache record."""

        try:
            del cls.Data[uid]
        except KeyError:
            pass
        else:
            if uid in cls.Accessed:
                del cls.Accessed[uid]
            if uid in cls.Size:
                del cls.Size[uid]
                cls.Order.remove(uid)

    @classmethod
    def delete(cls, fn=None, *args, **kwargs):
        """Delete cache for a function.
        If no arguments are given, all instances will be cleared.
        Give arguments to only delete a specific cache value.
        """

        if fn is None:
            cls.Data = {}
            cls.Accessed = {}
            cls.Size = {None: 0}
            cls.Order = []

        elif args or kwargs:
            cls._delete_uid(fingerprint(partial(extract_decorated_func(fn), *args, **kwargs)))

        else:
            func_hash = hash(extract_decorated_func(fn))
            for key in {k for k in cls.Data.keys() if k[0] == func_hash}:
                cls._delete_uid(key)

    @classmethod
    def _count(cls, dct, fn=None, *args, **kwargs):
        """Count a number of occurances."""

        # Count all records
        if fn is None:
            return sum(dct.values())

        # Count records for a particular function with arguments
        if args or kwargs:
            return dct.get(fingerprint(partial(extract_decorated_func(fn), *args, **kwargs)), 0)

        # Count records for a particular function
        func_hash = hash(extract_decorated_func(fn))
        return sum(v for k, v in dct.items() if k[0] == func_hash)

    @classmethod
    def hits(cls, fn=None, *args, **kwargs):
        """Count the number of times the cache has been used."""

        return cls._count(cls.Hits, fn, *args, **kwargs)

    @classmethod
    def misses(cls, fn=None, *args, **kwargs):
        """Count the number of times the cache has been regenerated."""

        return cls._count(cls.Misses, fn, *args, **kwargs)
