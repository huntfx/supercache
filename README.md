# supercache
Easy to use and intuitive caching for functions and methods.

Supercache has been designed to work as a decorator where it can be quickly added to any number of functions, while still allowing for the fine tuning of settings on an individual basis.

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
from supercache import Cacbe
from supercache.engine import Memory
cache = Cache(engine=Memory(mode=Memory.FIFO, ttl=600, count=100000, size=100000))
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


### cache(_keys=None, ignore=None, ttl=None, size=None, precalculate=False_)

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

### cache.delete(_func=None, *args, **kwargs_)
- `cache.delete()`: Delete all cached data.
- `cache.delete(func)`: Delete all cached data for `func`.
- `cache.delete(func, 1, b=2)`: Delete the cached data for `func(1, b=2)`.

### cache.hits(_func=None, *args, **kwargs_)
Return a count of how many times the cache was read for the given parameters.

- `cache.hits()`: Number of total cache hits.
- `cache.hits(func)`: Number of cache hits for `func`.
- `cache.hits(func, 1, b=2)`: Number of cache hits specifically for `func(1, b=2)`.

### cache.misses(_func=None, *args, **kwargs_)
Return a count of how many times the cache was generated for the given parameters.

- `cache.misses()`: Number of total cache misses.
- `cache.misses(func)`: Number of cache misses for `func`.
- `cache.misses(func, 1, b=2)`: Number of cache misses specifically for `func(1, b=2)`.

### cache.exists(_func=None, *args, **kwargs_)
Get if the cache exists for a particular input.

- `cache.exists()`: If any cache exists.
- `cache.exists(func)`: If any cache exists for `func`.
- `cache.exists(func, 1, b=2)`: If any cache exists specifically for `func(1, b=2)`.

## Planned
- Support for SQLite
- Support for Redis

## Limitations
- Unable to cache if unhashable arguments are used
- Python will assign the same hash to two classes with the same inheritance if they are both initialised on the same line (fortunately this shouldn't ever happen outside of testing)
- `classmethods`, `staticmethods` and `properties` can only be cached if the cache decorator is executed first
