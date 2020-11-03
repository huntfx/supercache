# supercache
Easy to use caching for functions and methods.

Supercache has been designed as a decorator to work with functions and methods, to provide almost instant repeat executions with only a single extra line of code. It acts as an interface to the cache engine, which can be anything from caching in memory to using Redis (provided it's been coded).

Please note that using the decorator adds a small amount of overhead as it was designed for conveniance and stability over performance. It's possible that caching a very simple function could result in worse performance (it roughly takes 1 second per 40,000 executions).

## Installation
    pip install supercache

## Usage
```python
from supercache import cache

# Basic cache
@cache()
def function(x, y=None):
    return(x, y)

# Set timeout
@cache(ttl=60)
def function(x, y=None):
    return(x, y)

# Ignore the y argument
@cache(ignore=['y'])
def function(x, y=None):
    return(x, y)

# Ignore anything after the first 2 arguments
@cache(keys=[0, 1])
def function(x, y=None, *args, **kwargs):
    return(x, y)


# Set up a custom cache engine
from supercache.engine import Memory

cache = Cache(engine=Memory(mode=Memory.FIFO, ttl=600, count=100000, size=100000))


# Manually handle cache to reduce the decorator overhead
# This is in danger of collisions if the key is not unique
from supercache.exceptions import CacheError

def function(x, y=None):
    key = 'function;{};{}'.format(x, y)
    try:
        return cache.get(key)
    except CacheError:
        value = (x, y)
        cache.put(key, value)
        return value
```

### Supported Types
```python
# Functions
@cache()
def function():
    pass

# Methods
class Class(object):
    @cache()
    def method(self):
        pass

# Generators/iterators
@cache()
def generator():
    yield

# Lambdas
func = cache()(lambda: None)
```

## API Reference

### @cache(_keys=None, ignore=None, ttl=None, precalculate=False_)

#### keys
Set which parameters of the function to use in generating the cache key. All available parameters will be used by default.

These can be in the format of `int`, `str`, `slice` (useful for `*args`), or `regex` (useful for `**kwargs`)

#### ignore
Set which parameters to ignore when generating the cache key. This will override any settings provided in `keys`.

These can also be in the format of `int`, `str`, `slice` or `regex`

#### ttl
Override the engine ttl setting to set how many seconds until the cache is invalidated.

#### precalculate
If the function being cached is a generator, setting this to `True` will convert the output to a `tuple` when first called, instead of returning the iterator.

The reason for this is the generator caching has a lot of overhead, which could become very noticable when calling a simple generator thousands of times.

### cache.get(_key_):
__Alias:__ `cache[key]`

Read an item of cache, or raise an error if it doesn't exist.

### cache.put(_key, value, **kwargs_):
__Alias:__ `cache[key] = value`

Set a new item of cache.

### cache.delete(_key=None, *args, **kwargs_)
__Alias:__ `del cache[key]`

Delete cache for a key or function.
- `cache.delete()`: Delete all cached data.
- `cache.delete(key)`: Delete cached data for a specific `key`.
- `cache.delete(func)`: Delete cached data for every execution of `func`.
- `cache.delete(func, 1, b=2)`: Delete the cached data for `func(1, b=2)`.

### cache.hits(_key=None, *args, **kwargs_)
Return a count of how many times the cache was read for a key or function.

- `cache.hits()`: Number of total cache hits.
- `cache.hits(key)`: Number of hits for a specific `key`.
- `cache.hits(func)`: Number of cache hits for every execution of `func`.
- `cache.hits(func, 1, b=2)`: Number of cache hits specifically for `func(1, b=2)`.

### cache.misses(_key=None, *args, **kwargs_)
Return a count of how many times the cache was generated for a key or function.

- `cache.misses()`: Number of total cache misses.
- `cache.misses(key)`: Number of misses for a specific `key`.
- `cache.misses(func)`: Number of cache misses for every execution of `func`.
- `cache.misses(func, 1, b=2)`: Number of cache misses specifically for `func(1, b=2)`.

### cache.exists(_key=None, *args, **kwargs_)
Get if the cache exists for a key or function.

- `cache.exists()`: If any cache exists.
- `cache.exists(key)`: If `key` exists in cache.
- `cache.exists(func)`: If any execution of `func` exists in cache.
- `cache.exists(func, 1, b=2)`: If `func(1, b=2)` exists in cache.

### engine.Memory(_mode=LRU, ttl=None, count=None, size=None_)

#### Mode
Set the mode for purging cache. Options are FIFO (first in first out), FILO (first in last out), LRU (least recently used), MRU (most recently used) or LFU (least frequently used).

#### ttl
Set how many seconds until the cache is invalidated.

#### count
Set the maximum amount of cached results.

#### size
Set the maximum size of the cache in bytes. This a soft limit, where the memory will be allocated first, then older cache will be deleted until it is back under the limit.

The latest execution will always be cached, even if the maximum size is set to smaller than the result.

## Planned
- Support for SQLite
- Support for memcached
- Support for Redis

## Limitations
- Unable to cache if unhashable arguments are used
- Python will assign the same hash to two classes with the same inheritance if they are both initialised on the same line (fortunately this shouldn't ever happen outside of testing)
- `classmethods`, `staticmethods` and `properties` can only be cached if the cache decorator is executed first
