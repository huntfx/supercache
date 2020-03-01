# supercache
Cache the result of a function so subsequent calls are faster. For finer control, certain arguments can be included or excluded.

Currently timeouts are supported, with a future update bringing size limits.

### Supported Types
- functions
- generators/iterators
- methods
- properties

### Limitations
- Unable to cache anything using unhashable arguments
