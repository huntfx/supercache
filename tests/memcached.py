import os
import sys
import unittest
import uuid
import time

sys.path.append(os.path.normpath(__file__).rsplit(os.path.sep, 2)[0])
from supercache import Cache, engine


# Cache needs to be initialised outside or it causes socket errors
cache = Cache(engine=engine.Memcached())
cache_long = Cache(engine=engine.Memcached(ttl=100000))
cache_short = Cache(engine=engine.Memcached(ttl=1))


class TestBase(unittest.TestCase):
    def setUp(self):
        self.cache = cache
        self.cache_long = cache_long
        self.cache_short = cache_short

        # Generate unique group name
        for i, c in enumerate((self.cache, self.cache_long, self.cache_short)):
            c.group = uuid.uuid4().hex


class TestFunction(TestBase):
    def test_simple(self):
        @self.cache()
        def func(x=None):
            return uuid.uuid4()
        self.assertEqual(func(), func())
        self.assertNotEqual(func(), func(1))

    def test_duplicate(self):
        @self.cache()
        def func(x=None):
            return uuid.uuid4()
        result = func()
        @self.cache()
        def func(x=None):
            return uuid.uuid4()
        result2 = func()
        self.assertNotEqual(result, result2)

    def test_timeout_global(self):
        @self.cache_short()
        def func():
            return uuid.uuid4()
        result = func()
        self.assertEqual(result, func())
        time.sleep(1.1)
        result2 = func()
        self.assertNotEqual(result2, result)
        self.assertEqual(result2, func())
        time.sleep(1.1)
        result3 = func()
        self.assertNotEqual(result3, result2)
        self.assertNotEqual(result3, result)
        self.assertEqual(result3, func())

    def test_timeout_local(self):
        @self.cache(ttl=1)
        def func():
            return uuid.uuid4()
        result = func()
        self.assertEqual(result, func())
        time.sleep(1.1)
        result2 = func()
        self.assertNotEqual(result2, result)
        self.assertEqual(result2, func())
        time.sleep(1.1)
        result3 = func()
        self.assertNotEqual(result3, result2)
        self.assertNotEqual(result3, result)
        self.assertEqual(result3, func())


class TestClass(TestBase):
    def test_method(self):
        class cls(object):
            @self.cache()
            def test(self):
                return uuid.uuid4()
        new = cls()
        self.assertEqual(new.test(), new.test())
        self.assertNotEqual(new.test(), cls().test())
        self.assertEqual(cls().test(), cls().test())  # Python limitation

    def test_classmethod(self):
        class cls(object):
            @classmethod
            @self.cache()
            def test1(cls):
                return uuid.uuid4()
            try:  # Fails on Python 2
                @self.cache()
                @classmethod
                def test2(cls):
                    return uuid.uuid4()
            except AttributeError:
                pass
        result = cls.test1()
        self.assertEqual(result, cls.test1())

    def test_staticmethod(self):
        class cls(object):
            @staticmethod
            @self.cache()
            def test1():
                return uuid.uuid4()
            try:  # Fails on Python 2
                @self.cache()
                @staticmethod
                def test2():
                    return uuid.uuid4()
            except AttributeError:
                pass
        result = cls.test1()
        self.assertEqual(result, cls.test1())

    def test_property(self):
        class cls(object):
            def __init__(self):
                self.uid = uuid.uuid4()
            @property
            @self.cache()
            def test1(self):
                return (self.uid, uuid.uuid4())
            try:  # Fails on Python 2
                @self.cache()
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


class TestLambda(TestBase):
    def test_simple(self):
        func = self.cache()(lambda a=1: uuid.uuid4())
        self.assertEqual(func(), func(1))
        self.assertNotEqual(func(), func(2))


class TestGenerator(TestBase):
    def test_simple(self):
        @self.cache()
        def test(x=0):
            yield uuid.uuid4()
        self.assertEqual(test(), test(0))
        self.assertNotEqual(test(), test(1))

    def test_precalculate(self):
        @self.cache(precalculate=True)
        def test(x=0):
            yield uuid.uuid4()
        self.assertIsInstance(test(), tuple)
        self.assertEqual(test(), test(0))
        self.assertNotEqual(test(), test(1))


class TestGroup(unittest.TestCase):
    def setUp(self):
        self.c1 = Cache(group='1')
        self.c2 = Cache(group='2')
        self.f1 = self.c1()(lambda: uuid.uuid4())
        self.f2 = self.c2()(lambda: uuid.uuid4())

    def test_simple(self):
        self.assertEqual(self.f1(), self.f1())
        self.assertEqual(self.f2(), self.f2())
        self.assertNotEqual(self.f1(), self.f2())

    def test_delete(self):
        result1 = self.f1()
        result2 = self.f2()
        self.c1.delete()
        self.assertNotEqual(result1, self.f1())
        self.assertEqual(result2, self.f2())
        self.c2.delete(self.f2, 1)
        self.assertEqual(result2, self.f2())
        self.c2.delete(self.f2)
        self.assertNotEqual(result2, self.f2())

    def test_delete_default(self):
        self.f1()
        self.c2.delete()
        self.assertTrue(self.c1.exists(self.f1))


if __name__ == '__main__':
    unittest.main()
