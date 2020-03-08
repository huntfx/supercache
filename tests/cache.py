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


class TestClass(unittest.TestCase):
    def test_method(self):
        class cls(object):
            @cache()
            def test(self):
                return uuid.uuid4()
        new = cls()
        self.assertEqual(new.test(), new.test())
        self.assertNotEqual(new.test(), cls().test())
        self.assertEqual(cls().test(), cls().test())  # Python limitation

    def test_classmethod(self):
        class cls(object):
            @classmethod
            @cache()
            def test1(cls):
                return uuid.uuid4()
            @cache()
            @classmethod
            def test2(cls):
                return uuid.uuid4()
        result = cls.test1()
        self.assertEqual(result, cls.test1())
        cache.delete(cls.test1)
        self.assertNotEqual(result, cls.test1())
        self.assertRaises(TypeError, cls.test2)

    def test_staticmethod(self):
        class cls(object):
            @staticmethod
            @cache()
            def test1():
                return uuid.uuid4()
            @cache()
            @staticmethod
            def test2():
                return uuid.uuid4()
        result = cls.test1()
        self.assertEqual(result, cls.test1())
        cache.delete(cls.test1)
        self.assertNotEqual(result, cls.test1())
        self.assertRaises(TypeError, cls.test2)

    def test_property(self):
        class cls(object):
            def __init__(self):
                self.uid = uuid.uuid4()
            @property
            @cache()
            def test1(self):
                return (self.uid, uuid.uuid4())
            @cache()
            @property
            def test2(self):
                return (self.uid, uuid.uuid4())
        new = cls()
        self.assertEqual(new.test1, new.test1)
        self.assertNotEqual(new.test1, cls().test1)
        self.assertRaises(TypeError, cls.test2)

if __name__ == "__main__":
    unittest.main()
