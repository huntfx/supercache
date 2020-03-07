import inspect
import sys

try:
    from .exceptions import UnhashableError

# For local testing
except (ImportError, SystemError):
    import os
    sys.path.append(os.path.normpath(__file__).rsplit(os.path.sep, 2)[0])
    from supercache.exceptions import UnhashableError


def generate_request(parameters, args, kwargs):
    """Generate the default request list."""

    request = list(range(max(len(parameters), len(args))))
    for key in sorted(kwargs):
        try:
            index = parameters.index(key)
        except ValueError:
            request.append(key)
        else:
            request.append(index)
    return request


def parse_input_list(lst, parameters, args, kwargs):
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
            for value in generate_request(parameters, args, kwargs)[key]:
                if isinstance(value, int):
                    ints.add(value)
                else:
                    strs.add(value)

        # Input given as keyword
        else:
            try:
                index = parameters.index(key)
            except ValueError:
                strs.add(key)
            else:
                strs.add(index)

        return sorted(sorted(ints) + sorted(strs))


def fingerprint(fn, args=None, kwargs=None, request=None, ignore=None):
    """Generate a unique fingerprint for the function."""

    if args is None:
        args = ()
    if kwargs is None:
        kwargs = {}

    # Get parameters from function
    try:
        argument_data = inspect.getfullargspec(fn.fget if isinstance(fn, property) else fn)
    except AttributeError:
        argument_data = inspect.getargspec(fn.fget if isinstance(fn, property) else fn)
        parameters = argument_data.args
    else:
        parameters = argument_data.args + argument_data.kwonlyargs

    # Get parameter default values as a dict
    if argument_data.defaults is None:
        default_values = {}
    else:
        default_values = dict(zip(reversed(parameters), reversed(argument_data.defaults)))

    # Use all parameters if none were chosen
    if request is None:
        request = generate_request(parameters, args, kwargs)

    else:
        request = parse_input_list(request, parameters, args, kwargs)

    if ignore is not None:
        ignore = parse_input_list(ignore, parameters, args, kwargs)
        request = [key for key in request if key not in ignore]

    # Build a list of the given arguments
    hash_list = []
    for i in request:
        if isinstance(i, int):
            # Get the argument at the index
            try:
                hash_list.append(args[i])

            # It may exist in *args
            except IndexError:
                try:
                    arg = args[i]

                # It may exist in **kwargs or have a default value
                except IndexError:
                    try:
                        param = parameters[i]

                    # It doesn't exist, so default to None
                    except IndexError:
                        hash_list.append(None)

                    else:
                        if param in kwargs:
                            hash_list.append(kwargs[param])
                        else:
                            hash_list.append(default_values.get(param))

        # It may exist in **kwargs
        else:
            hash_list.append(kwargs.get(i))

    try:
        return tuple(map(hash, hash_list))
    except TypeError:
        raise UnhashableError
