# supercache
Cache the result of a function so subsequent calls are faster. For finer control, certain arguments can be included or excluded.

### Supported Types
- functions
- generators/iterators
- methods
- properties

### Limitations
- Cache will fail if using unhashable arguments
- If two classes have the same inheritance, trying to create and hash them on the same line will result in both having the same hash
- Only able to cache classmethods, staticmethods and properties if the cache wrapper is added first
