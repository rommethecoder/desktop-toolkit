import unittest
from desktop_toolkit.audio import choose


class Audio(unittest.TestCase):
    def test_toggle(self):
        self.assertEqual(
            choose("headphones", "headphones", "speakers", ["headphones", "speakers"]),
            "speakers",
        )
        self.assertEqual(
            choose("speakers", "headphones", "speakers", ["headphones", "speakers"]),
            "headphones",
        )

    def test_missing_or_identical(self):
        for first, second, names in [
            ("missing", "b", ["b"]),
            ("same", "same", ["same"]),
        ]:
            with self.assertRaises(ValueError):
                choose("b", first, second, names)
