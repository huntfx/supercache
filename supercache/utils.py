import sys
from gc import get_referents
from types import ModuleType, FunctionType


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
