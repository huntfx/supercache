import inspect
import sys

try:
    from .exceptions import UnhashableError

# For local testing
except ImportError:
    import os
    sys.path.append(os.path.normpath(__file__).rsplit(os.path.sep, 2)[0])
    from supercache.exceptions import UnhashableError


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
        request = list(range(max(len(parameters), len(args))))
        for key in sorted(kwargs):
            try:
                index = parameters.index(key)
            except ValueError:
                request.append(key)
            else:
                request.append(index)

    # Parse the parameter list and try convert to int
    else:
        backup, request = request, []
        for key in backup:
            if isinstance(key, int):
                request.append(key)
            else:
                try:
                    index = parameters.index(key)
                except ValueError:
                    request.append(key)
                else:
                    request.append(index)

    # Parse the ignore list and try convert to int
    if ignore is not None:
        backup, ignore = ignore, []
        for key in backup:
            if isinstance(key, int):
                ignore.append(key)
            else:
                try:
                    ignore.append(parameters.index(key))
                except ValueError:
                    ignore.append(key)
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
