import base64
import inspect
import os
import sys
import time
from functools import partial, wraps
from types import FunctionType, MethodType

from . import exceptions
from .fingerprint import fingerprint
from .utils import *
from .engine import Memory
from .exceptions import CacheError


__version__ = '2.0.0'


class Memoize(object):
    """Function decorator for caching.

    Example:
        @cache(ttl=60)
        def func(): pass
    """

    __slots__ = ['cache', 'keys', 'ignore', 'ttl', 'precalculate']

    def __init__(self, cache, keys=None, ignore=None, ttl=None, precalculate=False):
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
        ttl (int):
            How many seconds the cache is valid for.
            Set to None for infinite.
        precalculate (bool):
            Convert a generator to a tuple.
        """

        self.cache = cache
        self.keys = keys
        self.ignore = ignore
        self.ttl = ttl
        self.precalculate = precalculate

    def __call__(self, func):

        @wraps(func)
        def wrapper(*args, **kwargs):

            try:
                f = partial(func, *args, **kwargs)
            except TypeError:
                if isinstance(func, (classmethod, staticmethod, property)):
                    raise TypeError("unhashable type '{}'".format(func.__class__.__name__))
                raise

            uid = fingerprint(f, keys=self.keys, ignore=self.ignore)

            # Fetch result from cache
            try:
                result = self.cache.get(uid)

            # Execute the function
            except CacheError:
                if inspect.isgeneratorfunction(func):
                    if self.precalculate:
                        result = tuple(f())
                    else:
                        result = GeneratorCache(f)
                else:
                    result = f()
                self.cache.put(uid, result, ttl=self.ttl)

            return result
        return wrapper


class Cache(object):
    """Interface to link code to the cache engine.

    This is used as either a decorator or a general key/value store.
    When used as a decorator, all function parameters will be read
    to ensure there's no collisions. This can be fine tuned to select
    or exclude certain parameters (eg. "print_output" won't have any
    effect on a returned value).
    """

    def __init__(self, group='', engine=Memory()):
        """Create the cache interface.

        Parameters:
            group (str): Prefixes all the cache keys.
                This is meant as a container of sorts, where setting a
                custom one will allow some operations to be performed
                on the entire group at once.
            engine (object): The backend handling all the cache.
                This should be set depending on the environment. If
                only running locally, then an in-memory engine will be
                sufficient, or sqlite could be used to keep the cache
                persistent across restarts. For multiple users,
                something like Redis would work better.
                Currently only the in-memory cache has been created.
        """
        self.engine = engine
        self.group = '<{}>.'.format(group)

    def __iter__(self):
        """Iterate through all keys."""
        prefix_len = len(self.group)
        for key in self.engine:
            if key[:prefix_len] == self.group:
                yield key[prefix_len:]

    def __call__(self, *args, **kwargs):
        """Create a new memoize instance."""
        return Memoize(self, *args, **kwargs)

    def __getitem__(self, key):
        """Conveniance method for Cache.get()."""
        return self.get(key)

    def __setitem__(self, key, value):
        """Conveniance method for Cache.put()."""
        return self.put(key, value)

    def __delitem__(self, key):
        """Conveniance method for Cache.delete()."""
        return self.delete(key)

    def get(self, key):
        """Get a cache key if it exists.
        If it doesn't exist, then an error will be raised.
        """
        return self.engine.get(self.group + key)

    def put(self, key, value, **kwargs):
        """Set a new cache value."""
        return self.engine.put(self.group + key, value, **kwargs)

    def delete(self, key=None, *args, **kwargs):
        """Delete an item of cache.
        Optionally pass in a function and arguments to delete the
        cached output.
        """
        # Delete all cache for the current group
        if key is None:
            count = 0
            for existing_key in tuple(self):
                count += self.delete(existing_key)
            return count

        if isinstance(key, (FunctionType, MethodType)):
            # Delete a specific function execution result
            if args or kwargs:
                key = fingerprint(partial(extract_decorated_func(key), *args, **kwargs))
                return int(self.delete(key))

            # Delete all keys belonging to a function
            else:
                key = str(hash(extract_decorated_func(key)))
                count = 0
                for existing_key in tuple(self):
                    if existing_key.startswith(key):
                        count += self.delete(existing_key)
                return count

        return int(self.engine.delete(self.group + key))

    def exists(self, key=None, *args, **kwargs):
        """Check if a key exists."""
        # Check for any key
        if key is None:
            try:
                next(iter(self))
            except StopIteration:
                return False
            return True

        # Check for function
        if isinstance(key, (FunctionType, MethodType)):
            func = extract_decorated_func(key)
            if args or kwargs:
                key = fingerprint(partial(func, *args, **kwargs))
                return self.exists(key)

            key = str(hash(func))
            for existing_key in self:
                if existing_key.startswith(key):
                    return True
            return False

        # Check for raw key
        return self.engine.exists(self.group + key)

    def _count(self, func, key=None, *args, **kwargs):
        """Count a number of occurances from the engine."""
        # Count total occurances
        if key is None:
            return sum(self._count(func, k) for k in self)

        # Count occurances of functions
        if isinstance(key, (FunctionType, MethodType)):
            fn = extract_decorated_func(key)
            if args or kwargs:
                key = fingerprint(partial(fn, *args, **kwargs))
                return func(self.group + key)

            key = str(hash(fn))
            return sum(self._count(func, k) for k in self if k.startswith(key))

        # Count occurance of an individual key
        return func(self.group + key)

    def hits(self, key=None, *args, **kwargs):
        """Count the number of times the cache has been used."""
        return self._count(self.engine.hits, key, *args, **kwargs)

    def misses(self, key=None, *args, **kwargs):
        """Count the number of times the cache has been regenerated."""
        return self._count(self.engine.misses, key, *args, **kwargs)


# Setup default cache
cache = Cache()
