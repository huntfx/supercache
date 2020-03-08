# supercache
Cache the result of a function so subsequent calls are faster.

### Supported Types
- functions
- generators/iterators
- methods
- properties
- lambdas

### Limitations
- Unable to cache output if unhashable arguments are used
- Python will assign the same hash to two classes with the same inheritance if they are both initialised on the same line
- classmethods, staticmethods and properties can only be cached if the cache wrapper is added first
