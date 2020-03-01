"""Cache/memoize function outputs.
See Cache class for instructions.

Supported:
    functions
    generators/iterators
    methods
    properties
    lambda
    *args
    **kwargs
    *args_ignore
    **kwargs_ignore

Limitations:
    Unhashable inputs are not supported

TODO:
    Cache *args with slice
    Cache **kwargs with modified regex
"""

from __future__ import absolute_import

import inspect
import sys
import time
from functools import partial
from types import GeneratorType


def add_metaclass(metaclass):
    """Class decorator for creating a class with a metaclass.

    Source: six.py
    """
    def wrapper(cls):
        orig_vars = cls.__dict__.copy()
        slots = orig_vars.get('__slots__')
        if slots is not None:
            if isinstance(slots, str):
                slots = [slots]
            for slots_var in slots:
                orig_vars.pop(slots_var)
        orig_vars.pop('__dict__', None)
        orig_vars.pop('__weakref__', None)
        if hasattr(cls, '__qualname__'):
            orig_vars['__qualname__'] = cls.__qualname__
        return metaclass(cls.__name__, cls.__bases__, orig_vars)
    return wrapper


class CacheError(Exception):
    """Used if there's an error when caching."""
    pass


class UnhashableError(CacheError):
    """The inputs contain unhashable types"""
    def __init__(self, *args, **kwargs):
        default_message = 'unhashable inputs incompatible with caching'
        if not (args or kwargs):
            args = (default_message,)
        super(UnhashableError, self).__init__(*args, **kwargs)


class InvalidResult(object):
    """Placeholder for an empty result, since result can be None.
    This just ensures any result can be used without issues.
    """
    pass


class GeneratorCache(object):
    """Cache the results from a generator.
    This will act as a normal generator, but append to a list.
    Once it is called again, if possible, the list will be read.

    Only use this when the calculations are heavy. If the result is
    simply very large, convert to a list instead as it'll be faster.
    """
    def __init__(self, func, *args, **kwargs):
        self.func = func(*args, **kwargs)
        self.cache = []
        self.current = 0
        self.total = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self.current < self.total:
            value = self.cache[self.current]
        else:
            try:
                self.cache.append(next(self.func))
                self.total += 1
            except StopIteration:
                self.current = 0
                raise StopIteration

        result = self.cache[self.current]
        self.current += 1
        return result
    next = __next__


class Memoize(object):
    Data = {}
    def __init__(self, parent, func, group, timeout=None, force_hashable=True, optimise=True,
                 args_cache=None, kwargs_cache=None, args_ignore=None, kwargs_ignore=None):
        self.parent = parent
        self.__fn__ = func
        self.group = group
        self.timeout = timeout
        self.args = args_cache
        self.kwargs = kwargs_cache
        self.args_ignore = set(args_ignore)
        self.kwargs_ignore = set(kwargs_ignore)
        self.force_hashable = force_hashable
        self.optimise = optimise

        self.generator = inspect.isgeneratorfunction(self.__fn__)
        self.property = isinstance(self.__fn__, property)
        self._property_fset = self._property_fget = self._property_fdel = None
        if self.property:
            self.generator = inspect.isgeneratorfunction(self.__fn__.fget)
        else:
            self.generator = inspect.isgeneratorfunction(self.__fn__)

        self.hash = hash(self.__fn__)
        if self.group not in Memoize.Data:
            Memoize.Data[self.group] = {}
        if self.hash not in self.Data[self.group]:
            Memoize.Data[self.group][self.hash] = {}

    def __repr__(self):
        """Pretend it is the wrapped function."""
        return self.__fn__.__repr__()

    def __get__(self, instance, owner):
        """Get a class method or property."""
        if self.property:
            return self.__call__(instance)
        func = partial(self.__call__, instance)
        func.__fn__ = self.__fn__
        return func

    def __set__(self, instance, value):
        """Set a value if property.setter has been set."""
        if not self.property or not self._property_fset:
            raise AttributeError("can't set attribute")
        self._property_fset(instance, value)
        self.invalidate(instance)

    def __delete__(self, instance):
        """Delete a value if property.deleter has been set."""
        if not self.property or not self._property_fdel:
            raise AttributeError("can't delete attribute")
        self._property_fdel(instance)
        self.invalidate(instance)

    def setter(self, fset):
        """Define a setter wrap for a property."""
        if not self.property:
            raise AttributeError("'{}' object has no attribute 'setter'".format(self.__class__.__name__))
        self._property_fset = fset
        return self

    def deleter(self, fdel):
        """Define a deleter wrap for a property."""
        if not self.property:
            raise AttributeError("'{}' object has no attribute 'deleter'".format(self.__class__.__name__))
        self._property_fdel = fdel
        return self

    def __call__(self, *args, **kwargs):
        """Find if the result exists in cache or generate a new result."""
        # Skip cache if result is unhashable
        try:
            fingerprint = self.fingerprint(*args, **kwargs)
        except UnhashableError:
            if not self.force_hashable:
                if self.property:
                    return self.__fn__.fget(*args, **kwargs)
                return self.__fn__(*args, **kwargs)
            raise

        # Check the dictionaries contain all the keys
        try:
            data = Memoize.Data[self.group][self.hash]
        except KeyError:
            data = Memoize.Data[self.group][self.hash] = {}
        if fingerprint not in data:
            data[fingerprint] = {
                'result': InvalidResult,
                'time': 0,
                'hits': 0,
                'misses': 0,
            }
        data = data[fingerprint]

        # Refresh the function
        if data['result'] is InvalidResult or self.timeout is not None and time.time()-data['time'] > self.timeout:
            exec_func = self.__fn__.fget if self.property else self.__fn__
            if self.generator:
                if self.optimise:
                    result = tuple(exec_func(*args, **kwargs))
                else:
                    result = GeneratorCache(exec_func, *args, **kwargs)
            else:
                result = exec_func(*args, **kwargs)
            data['result'] = result
            data['time'] = time.time()
            data['misses'] += 1

        else:
            data['hits'] += 1

            # Reset the generator counter
            if self.generator and not self.optimise:
                data['result'].current = 0

        return data['result']

    def fingerprint(self, *args, **kwargs):
        """Generate a unique fingerprint for the function."""
        # Calculate parameters and default values
        if sys.version[0] == '2':
            argument_data = inspect.getargspec(self.__fn__.fget if self.property else self.__fn__)
            parameters = argument_data.args
            if argument_data.defaults is None:
                default_values = {}
            else:
                default_values = dict(zip(reversed(parameters), reversed(argument_data.defaults)))
        else:
            argument_data = inspect.getfullargspec(self.__fn__.fget if self.property else self.__fn__)
            parameters = argument_data.args + argument_data.kwonlyargs
            default_values = argument_data.kwonlydefaults or {}

        hash_list = []
        arg_request = self.args
        kwarg_request = self.kwargs
        num_args = len(args)

        # Build the list of args first to take all possible parameters
        # Then add every kwarg that was input via **kwargs
        if not self.args and not self.kwargs:
            arg_request = range(max(len(parameters), len(args)))
            kwarg_request = sorted(key for key in kwargs if key not in default_values)

        # Match up args_ignore and kwargs_ignore
        if self.args_ignore:
            for index in self.args_ignore:
                try:
                    self.kwargs_ignore.add(parameters[index])
                except (KeyError, IndexError):
                    pass
        if self.kwargs_ignore:
            for parameter in self.kwargs_ignore:
                try:
                    self.args_ignore.add(parameters.index(parameter))
                except ValueError:
                    pass

        if arg_request:
            for i in arg_request:
                if i not in self.args_ignore:
                    # Argument is provided normally - args=[0, 1, 2] | func('x', 'y', 'z')
                    if i < num_args:
                        hash_list.append(args[i])
                    else:
                        # Argument is provided as a kwarg - args=[0, 1, 2] | func(a='x', b='y', c='z')
                        try:
                            param = parameters[i]
                        except IndexError:
                            param = None

                        # The same argument and kwarg is provided - args=[0], kwargs=['a'] | func(a='x')
                        if param in kwargs:
                            hash_list.append(kwargs[param])

                        # Argument is not provided - args=[0, 1, 2] | func()
                        # A KeyError here can mask an invalid argument TypeError,
                        #  but it can also mean an index higher than the *args count.
                        else:
                            hash_list.append(default_values.get(param))

        # Convert args to kwargs (see below for example)
        # Start the loop instead of from the latest index, to handle cases
        #  where one parameter is defined as both an arg and a kwarg.
        argument_kwargs = {}
        try:
            for i in range(num_args):
                if i not in self.args_ignore:
                    param = parameters[i]
                    argument_kwargs[param] = args[i]
        except IndexError:
            pass

        if kwarg_request:
            for key in kwarg_request:
                if key not in self.kwargs_ignore:
                    # Keyword argument is provided
                    if key in kwargs:
                        hash_list.append(kwargs[key])

                    # Keyword arguments are input as arguments - kwargs=['a', 'b', 'c'] | func('x', 'y', 'z')
                    elif key in argument_kwargs:
                        hash_list.append(argument_kwargs[key])

                    # Keyword argument is not provided - kwargs=['b'] | func(123)
                    # It will either use the default value, or None if it's expected from **kwargs
                    else:
                        hash_list.append(default_values.get(key, None))

        try:
            return tuple(map(hash, hash_list))
        except TypeError:
            raise UnhashableError

    def invalidate(self, *args, **kwargs):
        """Invalidate the cache for a certain input.
        This should only be used if the data has changed.
        """
        data = Memoize.Data[self.group][self.hash]
        if data:
            fingerprint = self.fingerprint(*args, **kwargs)
            if fingerprint in data:
                del data[fingerprint]
                return True
        return False

    @property
    def cache(self):
        """View the cache currently stored."""
        return Memoize.Data[self.group][self.hash]

    @cache.deleter
    def cache(self):
        """Add a way to delete the cache."""
        Memoize.Data[self.group][self.hash] = {}


class CacheMeta(type):
    def __getitem__(self, item):
        """Set data under the name of a group."""
        return partial(Cache, group=item)

    def __delitem__(self, item):
        """Delete all the memoized data in a group."""
        Memoize.Data[item] = {}


@add_metaclass(CacheMeta)
class Cache(object):
    def __init__(self, *args, **kwargs):
        """Setup the cache.

        Each cache is unique to the specific function, with optional
        arguments that will differntiate the outputs. Not all inputs
        will change the output, so any that do must be defined.

        Take a function "format_data", that has the parameters
        "print_messages" and "json_convert". No matter if printing
        or not, the output won't change, so we can ignore this.
        However, the value of "json_convert" will change the output,
        so that needs to be included in the cache.

        These can be put in as either arg indexes or kwarg strings.
        Any argument is compatible with both ways, with the exception
        of *args and **kwargs

        Example:
            # Cache on the values of "a", "b", "c" and "d"
            >>> @Cache(0, 1, 'c', 'd', timeout=60)
            >>> def func(a, b=2, c=3, **kwargs): pass

        Parameters:
            args (list): Indexes or text of each argument to cache.
                If the first argument is set to Cache.All, then every
                input argument will be used.

            timeout (int): How many seconds the cache is valid for
                If set to None, the timeout will be unlimited

            group (str): Define all cache under a group.
                This allows for easier deleting of specific things.
                This parameter is equivelent to using Cache[group].

            ignore (list): Indexes or text of each argument to ignore

            force_hashable (bool): Chose to ignore if parameters
                are not hashable. If not ignored, an UnhashableError
                exception will be raised.

            optimise(bool): Convert generators to tuples.
                This will give MUCH faster access, and is recommended
                to be enabled whenever a generator is in use.
                It is not enabled by default for complatibility.
                In the future this could contain other tweaks too.
        """
        self.args = []
        self.kwargs = []
        self.args_ignore = []
        self.kwargs_ignore = []
        for arg in args:
            if isinstance(arg, int):
                self.args.append(arg)
            else:
                self.kwargs.append(arg)

        for arg in kwargs.get('ignore', []):
            if isinstance(arg, int):
                self.args_ignore.append(arg)
            else:
                self.kwargs_ignore.append(arg)

        self.timeout = kwargs.get('timeout')
        self.group = kwargs.get('group')
        self.force_hashable = kwargs.get('force_hashable')
        self.optimise = kwargs.get('optimise')

    def __call__(self, func):
        return Memoize(
            self, func,
            group=self.group,
            timeout=self.timeout,
            args_cache=self.args,
            kwargs_cache=self.kwargs,
            args_ignore=self.args_ignore,
            kwargs_ignore=self.kwargs_ignore,
            force_hashable=self.force_hashable,
            optimise=self.optimise,
        )


if __name__ == '__main__':
    import random
    import uuid

    # Function test
    @Cache()
    def unique_id():
        return uuid.uuid4()
    del unique_id.cache

    first_id = unique_id()
    assert first_id == unique_id()
    del unique_id.cache
    assert first_id != unique_id()

    # Class test (no arguments)
    class Test(object):
        @Cache(ignore=['self'])
        def unique_id(self):
            return uuid.uuid4()

    first_id = Test().unique_id()
    assert first_id == Test().unique_id()
    second_id = Test().unique_id()
    assert second_id == first_id

    # Class test (arguments)
    class Test(object):
        def __init__(self, n):
            self.n = n
        def __hash__(self):
            return hash(self.n)
        @Cache(ignore=['validate'])
        def unique_id(self):
            return uuid.uuid4()

    first_id = Test(1).unique_id()
    assert first_id == Test(1).unique_id()
    assert first_id != Test(2).unique_id()

    # Generator test
    @Cache(optimise=False)
    def gen():
        for i in range(3):
            yield i
            yield uuid.uuid4()

    assert 1 in gen()
    assert 1 in gen()
    assert list(gen()) == list(gen())
    assert not isinstance(gen(), tuple)

    @Cache(optimise=True)
    def gen():
        for i in range(3):
            yield uuid.uuid4()
    assert gen() == gen()
    assert isinstance(gen(), tuple)

    # Property test
    class Test(object):
        def __init__(self):
            self.n = uuid.uuid4()
        @Cache()
        @property
        def test(self):
            return self.n
        @test.setter
        def test(self, value):
            self.n = value
        @test.deleter
        def test(self):
            self.n = uuid.uuid4()

    t1 = Test()
    first_value = t1.test
    assert first_value == t1.test
    t1.test = second_value = uuid.uuid4()
    assert first_value != second_value
    del t1.test
    assert second_value != t1.test

    t2 = Test()
    assert t2.test != t1.test

    # Lambda test
    random.seed(0)
    test = lambda: [random.randint(0, 10000) for i in range(10)]
    test = Cache()(test)
    result = test()
    assert result == test()
    del test.cache
    assert result != test()

    # Property + generator test
    class Test(object):
        @Cache(optimise=False, ignore=['self'])
        @property
        def test(self):
            for i in range(3):
                yield i
                yield uuid.uuid4()
    assert list(Test().test) == list(Test().test)
    assert not isinstance(Test().test, tuple)

    class Test(object):
        @Cache(optimise=True, ignore=['self'])
        @property
        def test(self):
            for i in range(3):
                yield i
                yield uuid.uuid4()
    assert Test().test == Test().test
    assert isinstance(Test().test, tuple)
