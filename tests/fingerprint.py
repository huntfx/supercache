import os
import re
import sys
import unittest
from functools import partial

sys.path.append(os.path.normpath(__file__).rsplit(os.path.sep, 2)[0])
from supercache.fingerprint import fingerprint


class TestFuncInputs(unittest.TestCase):
    def test_single_arg(self):
        def f(a): pass
        self.assertEqual(fingerprint(partial(f, 1)), fingerprint(partial(f, 1)))
        self.assertNotEqual(fingerprint(partial(f, 1)), fingerprint(partial(f, 2)))

    def test_single_arg_as_kwarg(self):
        def f(a): pass
        self.assertEqual(fingerprint(partial(f, a=1)), fingerprint(partial(f, a=1)))
        self.assertNotEqual(fingerprint(partial(f, a=1)), fingerprint(partial(f, a=2)))
        self.assertEqual(fingerprint(partial(f, a=1)), fingerprint(partial(f, 1)))
        self.assertNotEqual(fingerprint(partial(f, a=1)), fingerprint(partial(f, 2)))

    def test_single_arg_lambda(self):
        f = lambda a: None
        self.assertEqual(fingerprint(partial(f, a=1)), fingerprint(partial(f, a=1)))
        self.assertNotEqual(fingerprint(partial(f, a=1)), fingerprint(partial(f, a=2)))
        self.assertEqual(fingerprint(partial(f, a=1)), fingerprint(partial(f, 1)))
        self.assertNotEqual(fingerprint(partial(f, a=1)), fingerprint(partial(f, 2)))

    def test_double_arg(self):
        def f(a, b): pass
        self.assertEqual(fingerprint(partial(f, 1, 2)), fingerprint(partial(f, 1, 2)))
        self.assertEqual(fingerprint(partial(f, 1, b=2)), fingerprint(partial(f, a=1, b=2)))
        self.assertNotEqual(fingerprint(partial(f, a=1, b=2)), fingerprint(partial(f, a=1, b=1)))
        self.assertEqual(fingerprint(partial(f, a=1, b=2)), fingerprint(partial(f, b=2, a=1)))

    def test_defaults(self):
        def f(a=1, b=2): pass
        self.assertEqual(fingerprint(partial(f, 1, 2)), fingerprint(partial(f)))
        self.assertEqual(fingerprint(partial(f, 1, 2)), fingerprint(partial(f, a=1, b=2)))
        self.assertNotEqual(fingerprint(partial(f, 1, b=None)), fingerprint(partial(f, 1)))

    def test_args(self):
        def f(*args): pass
        self.assertEqual(fingerprint(partial(f, 1, 2, 3)), fingerprint(partial(f, 1, 2, 3)))
        self.assertNotEqual(fingerprint(partial(f, 1, 2, 3)), fingerprint(partial(f, 1, 2)))
        self.assertNotEqual(fingerprint(partial(f)), fingerprint(partial(f, None)))

    def test_args_with_argument(self):
        def f(a, b, *args): pass
        self.assertEqual(fingerprint(partial(f, 1, 2, 3)), fingerprint(partial(f, 1, 2, 3)))
        self.assertNotEqual(fingerprint(partial(f, 1, 2, 3)), fingerprint(partial(f, 1, 2)))

    def test_kwargs(self):
        def f(*kwargs): pass
        self.assertEqual(fingerprint(partial(f, a=1, b=2, c=3)), fingerprint(partial(f, c=3, b=2, a=1)))
        self.assertNotEqual(fingerprint(partial(f, a=1, b=2, c=3)), fingerprint(partial(f, a=1, b=2)))

    def test_kwargs_with_argument(self):
        def f(a=1, b=2, **kwargs): pass
        self.assertEqual(fingerprint(partial(f)), fingerprint(partial(f, b=2, a=1)))
        self.assertNotEqual(fingerprint(partial(f)), fingerprint(partial(f, a=1, b=2, c=None)))

    def test_args_kwargs(self):
        def f(a, b=2, *args, **kwargs): pass
        self.assertEqual(fingerprint(partial(f, 1)), fingerprint(partial(f, 1, 2)))
        self.assertEqual(fingerprint(partial(f, 1)), fingerprint(partial(f, 1, b=2)))
        self.assertEqual(fingerprint(partial(f, 1, 2, c=3)), fingerprint(partial(f, 1, b=2, c=3)))
        self.assertNotEqual(fingerprint(partial(f, 1, 2, 3)), fingerprint(partial(f, 1, 2, c=3)))

    def test_duplicate_inputs(self):
        def f(a): pass
        self.assertRaises(TypeError, partial(fingerprint, partial(f, 1, a=2)))

    def test_unhashable_inputs(self):
        def f(a): pass
        self.assertRaises(TypeError, partial(fingerprint, partial(f, dict(a=1))))

    def test_kwonlyargs(self):
        def f(a, *args, b=2, **kwargs): pass
        self.assertEqual(fingerprint(partial(f, 1, 0, b=2, c=3)), fingerprint(partial(f, 1, 0, c=3)))
        self.assertNotEqual(fingerprint(partial(f, 1, b=2, c=3)), fingerprint(partial(f, 1, None, b=2, c=3)))
        self.assertNotEqual(fingerprint(partial(f, 1, 0, 2)), fingerprint(partial(f, 1, 0)))
        self.assertNotEqual(fingerprint(partial(f, 1, 2)), fingerprint(partial(f, 1, b=2)))

    def test_different_functions(self):
        def f1(a=1, b=2): pass
        def f2(a, b): pass
        self.assertNotEqual(fingerprint(partial(f1, 1, 2)), fingerprint(partial(f2, 1, 2)))
        self.assertNotEqual(fingerprint(partial(f1)), fingerprint(partial(f2, 1, 2)))


class TestCacheInputs(unittest.TestCase):
    def test_simple_keys(self):
        def f(a, b): pass
        self.assertEqual(fingerprint(partial(f, 1, 2), keys=[0, 1]), fingerprint(partial(f, 1, 2), keys=['a', 'b']))
        self.assertNotEqual(fingerprint(partial(f, 1, 2), keys=[0, 1]), fingerprint(partial(f, 1, 3), keys=['a', 'b']))
        self.assertEqual(fingerprint(partial(f, 1, 2), keys=[0]), fingerprint(partial(f, 1, 3), keys=['a']))

    def test_simple_ignore(self):
        def f(a, b): pass
        self.assertEqual(fingerprint(partial(f, 1, 2), ignore=[1]), fingerprint(partial(f, 1, 3), keys=['a']))
        self.assertEqual(fingerprint(partial(f, 1, 2), keys=[0, 1], ignore=[1]), fingerprint(partial(f, 1, 3), ignore=[1]))
        self.assertNotEqual(fingerprint(partial(f, 1, 2), ignore=[1]), fingerprint(partial(f, 1, 2), ignore=[0]))

    def test_keys_ignore_mixed(self):
        def f(a, b): pass
        self.assertEqual(fingerprint(partial(f, 1, 2), keys=[1], ignore=[1]), fingerprint(partial(f, 5, 7), keys=[]))
        self.assertEqual(fingerprint(partial(f, 1, 2), keys=[1, 2], ignore=[1]), fingerprint(partial(f, 5, 2), keys=[2]))
        self.assertNotEqual(fingerprint(partial(f, 1, 2), keys=[1, 2], ignore=[2]), fingerprint(partial(f, 5, 2), keys=[2]))

    def test_slice(self):
        def f(a=1, b=2, c=3, d=4): pass
        fn = partial(f, 1, 1, 1, 1)
        self.assertEqual(fingerprint(fn, keys=[slice(2, 4)]), fingerprint(fn, keys=[2, 3]))
        self.assertNotEqual(fingerprint(fn, keys=[slice(2, 4)]), fingerprint(fn))

        self.assertEqual(fingerprint(fn, keys=[slice(2, None)]), fingerprint(fn, keys=[2, 3]))
        self.assertNotEqual(fingerprint(fn, keys=[slice(2, None)]), fingerprint(fn))
        self.assertEqual(fingerprint(fn, keys=[slice(None, 3)]), fingerprint(fn, keys=[0, 1, 2]))
        self.assertNotEqual(fingerprint(fn, keys=[slice(None, 3)]), fingerprint(fn))
        self.assertEqual(fingerprint(fn, keys=[slice(None, None)]), fingerprint(fn))
        self.assertEqual(fingerprint(fn, keys=[slice(None, None)]), fingerprint(fn, keys=[slice(0, 4)]))
        self.assertEqual(fingerprint(fn, keys=[slice(None, None), 1, 2]), fingerprint(fn))

        self.assertEqual(fingerprint(fn, keys=[slice(None, None, 2)]), fingerprint(fn, keys=[0, 2]))
        self.assertNotEqual(fingerprint(fn, keys=[slice(None, None, 2)]), fingerprint(fn, keys=[1, 3]))
        self.assertNotEqual(fingerprint(fn, keys=[slice(None, None, 2)]), fingerprint(fn))

        self.assertEqual(fingerprint(fn, ignore=[slice(2, 4)]), fingerprint(fn, keys=[0, 1]))
        self.assertEqual(fingerprint(fn, ignore=[slice(3, None)]), fingerprint(fn, keys=[slice(None, 3)]))

        def f(*args): pass
        fn = partial(f, *([1] * 30))
        self.assertEqual(
            fingerprint(fn, keys=[slice(None, None, 3)], ignore=[slice(None, None, 5)]),
            fingerprint(fn, keys=[3, 6, 9, 12, 18, 21, 24, 27])
        )

    def test_regex(self):
        def f(a=1, b=2, arg_c=3, arg_d=4): pass
        fn = partial(f, 1, 1, 1, 1)
        regex = re.compile('arg_.*')

        self.assertEqual(fingerprint(fn, keys=[regex]), fingerprint(fn, keys=['arg_c', 3]))
        self.assertNotEqual(fingerprint(fn, keys=[regex]), fingerprint(fn))
        self.assertEqual(fingerprint(fn, ignore=[regex]), fingerprint(fn, keys=[0, 1]))
        self.assertEqual(fingerprint(fn, ignore=[regex]), fingerprint(fn, ignore=[2, 3]))

        self.assertEqual(fingerprint(fn, keys=['arg_c'], ignore=[regex]), fingerprint(fn, keys=[]))


if __name__ == '__main__':
    unittest.main()
