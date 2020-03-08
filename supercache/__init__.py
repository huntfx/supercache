import os
import sys
import time
from functools import partial, wraps

sys.path.append(os.path.normpath(__file__).rsplit(os.path.sep, 2)[0])
from supercache.fingerprint import fingerprint


class cache(object):
    Data = {}
    Accessed = {}
    def __init__(self, keys=None, ignore=None, timeout=None):
        self.keys = keys
        self.ignore = ignore
        self.timeout = timeout

    def __call__(self, fn):
        """Setup function cache."""

        @wraps(fn)
        def wrapper(*args, **kwargs):
            f = partial(fn, *args, **kwargs)
            uid = fingerprint(f, keys=self.keys, ignore=self.ignore)
            current_time = time.time()

            if (uid not in self.Data
                or (self.timeout is not None
                    and current_time - self.timeout > self.Accessed.get(uid, current_time))):
                self.Data[uid] = f()
                self.Accessed[uid] = current_time

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
