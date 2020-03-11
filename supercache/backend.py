from collections import defaultdict


class DictCache(object):
    """Memory based caching."""

    Result = 0
    Accessed = 1
    Size = 2
    Order = 3
    Hits = 4
    Misses = 5

    defaults = lambda: [
        {},  # Result
        {},  # Accessed
        {None: 0},  # Size
        [],  # Order
        defaultdict(int),  # Hits
        defaultdict(int),  # Misses
    ]

    data = defaultdict(defaults)
