
class CacheError(Exception):
    """Used if there's an error when caching."""
    pass


class UnhashableError(CacheError, TypeError):
    """The inputs contain unhashable types"""

    def __init__(self, *args, **kwargs):
        default_message = 'unhashable inputs incompatible with caching'
        if not (args or kwargs):
            args = (default_message,)
        super(UnhashableError, self).__init__(*args, **kwargs)
