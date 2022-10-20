from django.test import TestCase


class TestNoop(TestCase):
    def test_noop(self):
        self.assertEqual(1, 1)
