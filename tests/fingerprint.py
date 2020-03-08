import os
import sys
import unittest
from functools import partial

sys.path.append(os.path.normpath(__file__).rsplit(os.path.sep, 2)[0])
from supercache.fingerprint import fingerprint


class TestFingerprint(unittest.TestCase):

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


if __name__ == "__main__":
    unittest.main()
