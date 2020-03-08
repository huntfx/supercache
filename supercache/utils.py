import sys
from gc import get_referents
from types import ModuleType, FunctionType


class GeneratorCache(object):
    """Cache the results from a generator."""

    __slots__ = ['fn', 'generator', 'cache', 'current', 'total']

    def __init__(self, fn):
        self.fn = fn
        self.generator = fn()
        self.cache = []
        self.current = 0
        self.total = 0

    def __repr__(self):
        return '<cached generator object {} at {}>'.format(
            self.fn.func.__name__, '{0:#018X}'.format(id(self))
        )

    def __iter__(self):
        return self

    def __next__(self):
        if self.current < self.total:
            value = self.cache[self.current]
        else:
            try:
                self.cache.append(next(self.generator))
                self.total += 1
            except StopIteration:
                self.current = 0
                raise StopIteration

        result = self.cache[self.current]
        self.current += 1
        return result
    next = __next__


def getsize(obj, ignore_types=(type, ModuleType, FunctionType)):
    """Summed size of object and members.
    Source: https://stackoverflow.com/a/30316760/2403000
    """

    if isinstance(obj, ignore_types):
        raise TypeError("getsize() does not take argument of type '{}'".format(type(obj)))
    seen_ids = set()
    size = 0
    objects = [obj]
    while objects:
        need_referents = []
        for obj in objects:
            if not isinstance(obj, ignore_types) and id(obj) not in seen_ids:
                seen_ids.add(id(obj))
                size += sys.getsizeof(obj)
                need_referents.append(obj)
        objects = get_referents(*need_referents)
    return size
