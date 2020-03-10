import inspect
import os
import sys
import unittest
import uuid
from functools import partial

sys.path.append(os.path.normpath(__file__).rsplit(os.path.sep, 2)[0])
from supercache import cache


class TestFunction(unittest.TestCase):
    def setUp(self):
        cache.delete()

    def test_simple(self):
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
            try:  # Fails on Python 2
                @cache()
                @classmethod
                def test2(cls):
                    return uuid.uuid4()
            except AttributeError:
                pass
        result = cls.test1()
        self.assertEqual(result, cls.test1())
        cache.delete(cls.test1)
        self.assertNotEqual(result, cls.test1())
        try:
            self.assertRaises(TypeError, cls.test2)
        except AttributeError:
            pass

    def test_staticmethod(self):
        class cls(object):
            @staticmethod
            @cache()
            def test1():
                return uuid.uuid4()
            try:  # Fails on Python 2
                @cache()
                @staticmethod
                def test2():
                    return uuid.uuid4()
            except AttributeError:
                pass
        result = cls.test1()
        self.assertEqual(result, cls.test1())
        cache.delete(cls.test1)
        self.assertNotEqual(result, cls.test1())
        try:
            self.assertRaises(TypeError, cls.test2)
        except AttributeError:
            pass

    def test_property(self):
        class cls(object):
            def __init__(self):
                self.uid = uuid.uuid4()
            @property
            @cache()
            def test1(self):
                return (self.uid, uuid.uuid4())
            try:  # Fails on Python 2
                @cache()
                @property
                def test2(self):
                    return (self.uid, uuid.uuid4())
            except AttributeError:
                pass
        new = cls()
        self.assertEqual(new.test1, new.test1)
        self.assertNotEqual(new.test1, cls().test1)
        try:
            self.assertRaises(TypeError, cls.test2)
        except AttributeError:
            pass


class TestStats(unittest.TestCase):
    def setUp(self):
        cache.delete()
        cache.Hits.clear()
        cache.Misses.clear()

    def test_counts(self):
        @cache()
        def f1(x=None): pass
        @cache()
        def f2(x=None): pass
        for f in (f1, f2):
            f()
            f()
            f(1)
            f(2)
            f(2)
            f(2)
            f(3)
        self.assertEqual(cache.hits(), 6)
        self.assertEqual(cache.misses(), 8)
        self.assertEqual(cache.hits(f1), 3)
        self.assertEqual(cache.misses(f1), 4)
        self.assertEqual(cache.hits(f1, None), 1)
        self.assertEqual(cache.misses(f1, None), 1)
        self.assertEqual(cache.hits(f1, 2), 2)
        self.assertEqual(cache.misses(f1, 2), 1)

    def test_exists(self):
        @cache()
        def f1(x=None): pass
        @cache()
        def f2(x=None): pass
        self.assertFalse(cache.exists())
        self.assertFalse(cache.exists(f1))
        self.assertFalse(cache.exists(f1, 1, 2))
        for f in (f1, f2):
            f()
            f()
            f(1)
            f(2)
            f(2)
            f(2)
            f(3)
        self.assertTrue(cache.exists())
        self.assertTrue(cache.exists(f1))
        self.assertTrue(cache.exists(f1, 2))
        self.assertFalse(cache.exists(f1, 4))
        cache.delete(f1)
        self.assertFalse(cache.exists(f1))
        self.assertTrue(cache.exists(f2))
        self.assertTrue(cache.exists())

class TestLambda(unittest.TestCase):
    def test_simple(self):
        func = cache()(lambda a=1: uuid.uuid4())
        self.assertEqual(func(), func(1))
        self.assertNotEqual(func(), func(2))


class TestGenerator(unittest.TestCase):
    def test_simple(self):
        @cache()
        def test(x=0):
            yield uuid.uuid4()
        self.assertEqual(test(), test(0))
        self.assertNotEqual(test(), test(1))

    def test_precalculate(self):
        @cache(precalculate=True)
        def test(x=0):
            yield uuid.uuid4()
        self.assertIsInstance(test(), tuple)
        self.assertEqual(test(), test(0))
        self.assertNotEqual(test(), test(1))


if __name__ == '__main__':
    unittest.main()
