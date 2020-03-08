import os
import sys
from functools import partial, wraps

sys.path.append(os.path.normpath(__file__).rsplit(os.path.sep, 2)[0])
from supercache.fingerprint import fingerprint


class cache(object):
    Data = {}
    def __init__(self, keys=None, ignore=None):
        self.keys = keys
        self.ignore = ignore

    def __call__(self, fn):
        """Setup function cache."""

        @wraps(fn)
        def wrapper(keys=None, ignore=None):
            f = partial(fn, *args, **kwargs)
            uid = fingerprint(f, keys=self.keys, ignore=self.ignore)
            if uid not in self.Data:
                self.Data[uid] = f()
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
