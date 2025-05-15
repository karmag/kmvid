import kmvid.data.resource as resource

import itertools
import testbase

class TestResource(testbase.Testbase):
    def test_clear(self):
        tm = resource.TimeMap(10)
        old = tm.__repr__()

        tm.set_crop_start(3)
        tm.set_speed(4)
        tm.clear()

        self.assertEqual(old, tm.__repr__())

    def test_crop_start(self):
        tm = resource.TimeMap(10)

        tm.set_crop_start(3)

        self.assertEqual(tm.get(0), 3)
        self.assertEqual(tm.get(5), 8)
        self.assertEqual(tm.get(10), None)
        self.assertEqual(tm.get_duration(), 7)

        tm.set_crop_start(8)

        self.assertEqual(tm.get(0), 8)
        self.assertEqual(tm.get(1), 9)
        self.assertEqual(tm.get(2), None)
        self.assertEqual(tm.get_duration(), 2)

    def test_crop_end(self):
        tm = resource.TimeMap(10)

        tm.set_crop_end(3)

        self.assertEqual(tm.get(0), 0)
        self.assertEqual(tm.get(5), 5)
        self.assertEqual(tm.get(7), None)
        self.assertEqual(tm.get_duration(), 7)

        tm.set_crop_end(5)

        self.assertEqual(tm.get(0), 0)
        self.assertEqual(tm.get(4), 4)
        self.assertEqual(tm.get(5), None)
        self.assertEqual(tm.get_duration(), 5)

    def test_crop_both(self):
        tm = resource.TimeMap(10)

        tm.set_crop_end(3)
        tm.set_crop_start(2)

        self.assertEqual(tm.get(0), 2)
        self.assertEqual(tm.get(4), 6)
        self.assertEqual(tm.get(6), None)
        self.assertEqual(tm.get_duration(), 5)

        tm.set_crop_start(5)
        tm.set_crop_end(1)

        self.assertEqual(tm.get(0), 5)
        self.assertEqual(tm.get(3), 8)
        self.assertEqual(tm.get(4), None)
        self.assertEqual(tm.get_duration(), 4)

    def test_speed(self):
        tm = resource.TimeMap(10)

        tm.set_speed(2)

        self.assertEqual(tm.get(0), 0)
        self.assertEqual(tm.get(1), 2)
        self.assertEqual(tm.get(4), 8)
        self.assertEqual(tm.get(5), None)
        self.assertEqual(tm.get_duration(), 5)

        tm.set_speed(0.5)

        self.assertEqual(tm.get(0), 0)
        self.assertEqual(tm.get(1), 0.5)
        self.assertEqual(tm.get(10), 5)
        self.assertEqual(tm.get(20), None)
        self.assertEqual(tm.get_duration(), 20)

    def test_speed_and_crop(self):
        calls = {"start": lambda tm: tm.set_crop_start(3),
                 "end"  : lambda tm: tm.set_crop_end(4),
                 "speed": lambda tm: tm.set_speed(2)}

        for keys in itertools.permutations(["start", "end", "speed"]):
            with self.subTest(calls = keys):
                tm = resource.TimeMap(10)

                for k in keys:
                    calls[k](tm)

                self.assertEqual(tm.get(0), 3)
                self.assertEqual(tm.get(1), 5)
                self.assertEqual(tm.get(2), None)
                self.assertEqual(tm.get_duration(), 1.5)

    def test_fit_into(self):
        tm = resource.TimeMap(10)
        tm.fit_into(5)

        self.assertEqual(tm.get(0), 0)
        self.assertEqual(tm.get(2), 4)
        self.assertEqual(tm.get(5), None)
        self.assertEqual(tm.get_duration(), 5)
