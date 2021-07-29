import hashlib
import inspect
import sys
import random
import re
from functools import partial
from types import GeneratorType, MethodType

try:
    Pattern = re.Pattern
except AttributeError:
    # < Python 3.7
    Pattern = re._pattern_type


def alternative_hash(value):
    """Quick way of doing a hash.
    This used to be hash(), but in Python 3 it is seeded and returns
    different values.
    Security is not an issue here so md5 is used as its cheap.
    """
    return hashlib.md5(repr(value).encode('utf-8')).hexdigest()


def default_keys(func, parameters, args, kwargs, kwonlyargs):
    """Generate the default request list."""
    arg_count = max(len(parameters), len(args))
    keys = list(range(arg_count))
    for kwonlyarg in kwonlyargs:
        keys.append(kwonlyarg)
    for key in sorted(kwargs):
        if key in kwonlyargs:
            continue
        try:
            index = parameters.index(key)
        except ValueError:
            keys.append(key)
        else:
            if index >= arg_count and index not in keys[:arg_count]:
                keys.append(index)
    return keys


def parse_key_list(lst, func, parameters, args, kwargs, kwonlyargs):
    """Parse a list of request/ignore arguments.

    There is a bit of overhead of adding to separate sets, as sorting
    with both str and int doesn't work.
    """
    ints = set()
    strs = set()
    for key in lst:
        # Input given as index
        if isinstance(key, int):
            ints.add(key)

        # Input given as slice
        # It's a lot easier here to slice the "default" request
        elif isinstance(key, slice):
            for value in default_keys(func, parameters, args, kwargs, kwonlyargs)[key]:
                if isinstance(value, int):
                    ints.add(value)
                else:
                    strs.add(value)

        else:
            # Input given as regex
            if isinstance(key, Pattern):
                keywords = []
                for kwarg in kwargs:
                    if key.search(kwarg):
                        keywords.append(kwarg)
                for param in parameters:
                    if param not in kwargs:
                        if key.search(param):
                            keywords.append(param)

            # Input given as keyword
            else:
                keywords = [key]

            for keyword in keywords:
                try:
                    index = parameters.index(keyword)
                except ValueError:
                    strs.add(keyword)
                else:
                    ints.add(index)

    return sorted(ints) + sorted(strs)


def fingerprint(fn, keys=None, ignore=None):
    """Generate a unique fingerprint for the function.
    fn must be a functools.partial instance with the arguments provided.
    """
    func = fn.func
    args = fn.args
    kwargs = fn.keywords
    if kwargs is None:  # Python 3.4 fix
        kwargs = {}

    # Get parameters from function
    try:
        argument_data = inspect.getfullargspec(func.fget if isinstance(func, property) else func)
    except AttributeError:
        argument_data = inspect.getargspec(func.fget if isinstance(func, property) else func)
        parameters = argument_data.args
        kwonlydefaults = {}
    else:
        parameters = argument_data.args
        kwonlydefaults = argument_data.kwonlydefaults
        if kwonlydefaults is None:
            kwonlydefaults = {}

    # Get parameter default values as a dict
    if argument_data.defaults is None:
        default_values = {}
    else:
        default_values = dict(zip(reversed(parameters), reversed(argument_data.defaults)))
    default_values.update(kwonlydefaults)

    # Generate a list of parameters to use
    if keys is None:
        keys = default_keys(func, parameters, args, kwargs, kwonlydefaults)
    else:
        keys = parse_key_list(keys, func, parameters, args, kwargs, kwonlydefaults)

    if ignore is not None:
        ignore = parse_key_list(ignore, func, parameters, args, kwargs, kwonlydefaults)
        keys = [key for key in keys if key not in ignore]

    # Convert the function object to a unique name
    try:
        try:
            func_name = func.__qualname__
        except AttributeError:
            func_name = func.__name__
    except AttributeError:
        func_name = str(func)
    try:
        namespace = inspect.stack()[-1][0].f_globals['__file__']
    except (KeyError, IndexError, AttributeError):
        namespace = '__main__'
    func_name = namespace + '.' + func_name

    # Build a list of the given arguments
    hash_list = [func_name, tuple(keys)]
    for key in keys:
        if isinstance(key, int):
            # Get the argument at the index
            try:
                value = args[key]

                # Raise error if key also exists in kwargs
                try:
                    param = parameters[key]
                except IndexError:
                    pass
                else:
                    if param in kwargs:
                        raise TypeError("{}() got multiple values for keyword arguments '{}'".format(func.__name__, parameters[key]))

            # It may exist in *args
            except IndexError:
                try:
                    value = args[key]

                # It may exist in **kwargs or have a default value
                except IndexError:
                    try:
                        param = parameters[key]

                    # It doesn't exist, so default to None
                    except IndexError:
                        value = None

                    else:
                        if param in kwargs:
                            value = kwargs[param]
                        else:
                            value = default_values.get(param)

        # It may exist in **kwargs
        # Extra hashing is required otherwise args[0] == kwargs[0]
        else:
            hash_list.append('__{}__'.format(key))
            if key in kwargs:
                value = kwargs[key]
            else:
                value = default_values.get(key)

        # Generators can cause cache collisons, so disable them
        if isinstance(value, GeneratorType):
            raise TypeError("unhashable function input type 'generator'")

        hash_list.append(value)

    try:
        return ';'.join(map(str, map(alternative_hash, hash_list)))

    # Raise custom exception message
    except TypeError:
        for item in hash_list:
            try:
                hash(item)
            except TypeError:
                raise TypeError("unhashable function input type '{}'".format(item.__class__.__name__))
