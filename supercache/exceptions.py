class CacheError(Exception):
    pass


class CacheExpired(CacheError):
    pass


class CacheNotFound(CacheError):
    pass


class CacheDatabaseLocked(CacheError):
    pass
