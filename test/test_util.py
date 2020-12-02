from unittest import TestCase
from pyshimmer.util import PeekQueue


class UtilTest(TestCase):

    def test_peek_queue(self):
        queue = PeekQueue()

        queue.put(1)
        queue.put(2)
        queue.put(3)

        self.assertEqual(queue.peek(), 1)
        queue.get()

        self.assertEqual(queue.peek(), 2)
        queue.get()

        self.assertEqual(queue.peek(), 3)
        queue.get()

        self.assertEqual(queue.peek(), None)
