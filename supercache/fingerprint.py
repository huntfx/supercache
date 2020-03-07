import inspect
import sys
import re
from functools import partial

try:
    from .exceptions import UnhashableError

# For local testing
except (ImportError, SystemError):
    import os
    sys.path.append(os.path.normpath(__file__).rsplit(os.path.sep, 2)[0])
    from supercache.exceptions import UnhashableError


def default_keys(parameters, args, kwargs):
    """Generate the default request list."""

    arg_count = max(len(parameters), len(args))
    request = list(range(arg_count))
    for key in sorted(kwargs):
        try:
            index = parameters.index(key)
        except ValueError:
            request.append(key)
        else:
            if index >= arg_count and index not in request[:arg_count]:
                request.append(index)
    return request


def parse_key_list(lst, parameters, args, kwargs):
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
            for value in default_keys(parameters, args, kwargs)[key]:
                if isinstance(value, int):
                    ints.add(value)
                else:
                    strs.add(value)

        # Input given as regex
        elif isinstance(key, re.Pattern):
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

    # Get parameters from function
    try:
        argument_data = inspect.getfullargspec(func.fget if isinstance(func, property) else func)
    except AttributeError:
        argument_data = inspect.getargspec(func.fget if isinstance(func, property) else func)
        parameters = argument_data.args
    else:
        parameters = argument_data.args

    # Get parameter default values as a dict
    if argument_data.defaults is None:
        default_values = {}
    else:
        default_values = dict(zip(reversed(parameters), reversed(argument_data.defaults)))
    default_values.update(argument_data.kwonlydefaults)

    # Generate a list of parameters to use
    if keys is None:
        keys = default_keys(parameters, args, kwargs, kwonlyargs=kwonlyargs)
    else:
        keys = parse_key_list(keys, parameters, args, kwargs)

    if ignore is not None:
        ignore = parse_key_list(ignore, parameters, args, kwargs)
        keys = [key for key in keys if key not in ignore]

    # Build a list of the given arguments
    hash_list = []
    for key in keys:
        if isinstance(key, int):
            # Get the argument at the index
            try:
                hash_list.append(args[key])

            # It may exist in *args
            except IndexError:
                try:
                    arg = args[key]

                # It may exist in **kwargs or have a default value
                except IndexError:
                    try:
                        param = parameters[key]

                    # It doesn't exist, so default to None
                    except IndexError:
                        hash_list.append(None)

                    else:
                        if param in kwargs:
                            hash_list.append(kwargs[param])
                        else:
                            hash_list.append(default_values.get(param))

        # It may exist in **kwargs
        # Also hash the key here, otherwise args[0] == kwargs[0]
        else:
            hash_list += [key, kwargs.get(key)]

    try:
        return tuple(map(hash, hash_list))
    except TypeError:
        raise UnhashableError
