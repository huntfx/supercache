import os
import sys
import unittest
import uuid
from functools import partial

sys.path.append(os.path.normpath(__file__).rsplit(os.path.sep, 2)[0])
from supercache import cache


class TestFunction(unittest.TestCase):
    def test_simple_func(self):
        @cache()
        def func(a=None):
            return uuid.uuid4()
        self.assertEqual(func(), func())
        self.assertNotEqual(func(), func(1))

    def test_cache_delete(self):
        @cache()
        def func(a=None):
            return uuid.uuid4()
        result = func()
        cache.delete(func)
        self.assertNotEqual(result, func())

    def test_size_limit(self):
        @cache(size=0)
        def func(a=None):
            return uuid.uuid4()
        result = func()
        self.assertEqual(result, func())
        func(1)
        self.assertNotEqual(result, func())

        @cache(size=100000)
        def func(a=None):
            return uuid.uuid4()
        result = func()
        self.assertEqual(result, func())
        func(1)
        self.assertEqual(result, func())

    def test_param_difference(self):
        @cache(size=10000)
        def func(a=None):
            return uuid.uuid4()
        result = func()
        @cache(size=100000)
        def func(a=None):
            return uuid.uuid4()
        result2 = func()
        self.assertNotEqual(result, result2)

        @cache(timeout=10)
        def func(a=None):
            return uuid.uuid4()
        result = func()
        @cache(timeout=20)
        def func(a=None):
            return uuid.uuid4()
        result2 = func()
        self.assertNotEqual(result, result2)


if __name__ == "__main__":
    unittest.main()
