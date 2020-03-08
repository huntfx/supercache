import os
import sys
import time
from collections import defaultdict
from functools import partial, wraps

sys.path.append(os.path.normpath(__file__).rsplit(os.path.sep, 2)[0])
from supercache.fingerprint import fingerprint
from supercache.utils import getsize


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

    __slots__ = ['keys', 'ignore', 'timeout', 'size']

    def __init__(self, keys=None, ignore=None, timeout=None, size=None):
        """Setup the cache options.

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
        """
        self.keys = keys
        self.ignore = ignore
        self.timeout = timeout
        self.size = size

    def __call__(self, fn):
        """Setup function cache."""

        @wraps(fn)
        def wrapper(*args, **kwargs):
            f = partial(fn, *args, **kwargs)
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
                            break

                        del self.Data[cache_id]
                        del self.Accessed[cache_id]
                        self.Size[None] -= self.Size.pop(cache_id)

            return self.Data[uid]
        return wrapper

    @classmethod
    def delete(cls, fn, *args, **kwargs):
        """Delete cache for a function.
        If no arguments are given, all instances will be cleared.
        Give arguments to only delete a specific cache value.
        """

        f = partial(fn.__wrapped__, *args, **kwargs)
        uid = fingerprint(f)
        if args or kwargs:
            try:
                del cls.Data[uid]
            except KeyError:
                pass
        else:
            for key in {k for k in cls.Data.keys() if k[0] == uid[0]}:
                try:
                    del cls.Data[key]
                except KeyError:
                    pass
