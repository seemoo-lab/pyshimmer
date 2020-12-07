# pyshimmer - API for Shimmer sensor devices
# Copyright (C) 2020  Lukas Magel

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
from io import BytesIO
from typing import Tuple
from unittest import TestCase

from pyshimmer.test_util import MockSerial
from pyshimmer.serial_base import SerialBase, BufferedReader, ReadAbort


class BufferedReaderTest(TestCase):

    def test_read(self):
        stream = BytesIO(b'thisisatest')

        # noinspection PyTypeChecker
        reader = BufferedReader(stream)

        r = reader.read(0)
        self.assertEqual(r, b'')

        r = reader.read(1)
        self.assertEqual(r, b't')

        r = reader.read(3)
        self.assertEqual(r, b'his')

        r = reader.read(0)
        self.assertEqual(r, b'')

        r = reader.read(7)
        self.assertEqual(r, b'isatest')

        self.assertRaises(ReadAbort, reader.read, 1)

    def test_peek(self):
        stream = BytesIO(b'thisisatest')

        # noinspection PyTypeChecker
        reader = BufferedReader(stream)

        r = reader.peek(0)
        self.assertEqual(r, b'')

        for i in range(2):
            r = reader.peek(4)
            self.assertEqual(r, b'this')

        r = reader.peek(11)
        self.assertEqual(r, b'thisisatest')

        self.assertRaises(ReadAbort, reader.peek, 20)

    def test_peek_read(self):
        stream = BytesIO(b'thisisatest')

        # noinspection PyTypeChecker
        reader = BufferedReader(stream)

        r = reader.peek(4)
        self.assertEqual(r, b'this')

        r = reader.read(2)
        self.assertEqual(r, b'th')

        r = reader.peek(6)
        self.assertEqual(r, b'isisat')

        r = reader.read(3)
        self.assertEqual(r, b'isi')

    def test_reset(self):
        stream = BytesIO(b'thisisatest')

        # noinspection PyTypeChecker
        reader = BufferedReader(stream)

        r = reader.read(2)
        self.assertEqual(r, b'th')

        r = reader.peek(4)
        self.assertEqual(r, b'isis')

        reader.reset()
        r = reader.read(3)
        self.assertEqual(r, b'ate')

        reader.reset()
        r = reader.peek(2)
        self.assertEqual(r, b'st')


class SerialBaseTest(TestCase):

    @staticmethod
    def create_sot() -> Tuple[MockSerial, SerialBase]:
        mock = MockSerial()

        # noinspection PyTypeChecker
        sot = SerialBase(mock)

        return mock, sot

    def test_flush_input_buf(self):
        mock, sot = self.create_sot()

        mock.test_put_read_data(b'test')
        r = sot.read(2)
        self.assertEqual(r, b'te')

        sot.flush_input_buffer()
        self.assertTrue(mock.test_input_flushed)
        self.assertRaises(ReadAbort, sot.read, 1)

    def test_write(self):
        mock, sot = self.create_sot()

        i = sot.write(b'this')
        self.assertEqual(i, 4)
        i = sot.write(b'')
        self.assertEqual(i, 0)
        i = sot.write(b'is')
        self.assertEqual(i, 2)

        r = mock.test_get_write_data()
        self.assertEqual(r, b'thisis')

        i = sot.write_byte(10)
        self.assertEqual(i, 1)
        i = sot.write_byte(16)
        self.assertEqual(i, 1)

        r = mock.test_get_write_data()
        self.assertEqual(r, b'\x0A\x10')

        i = sot.write_packed('<HBI', 0x0100, 0x20, 0x30000)
        self.assertEqual(i, 7)

        r = mock.test_get_write_data()
        self.assertEqual(r, b'\x00\x01\x20\x00\x00\x03\x00')

    def test_read(self):
        mock, sot = self.create_sot()

        mock.test_put_read_data(b'another test')

        r = sot.read(0)
        self.assertEqual(r, b'')

        r = sot.read(4)
        self.assertEqual(r, b'anot')

        mock.test_clear_read_buffer()
        mock.test_put_read_data(b'\x10')

        r = sot.read_byte()
        self.assertEqual(r, 16)

        mock.test_put_read_data(b'\x42')
        r = sot.read_packed('B')
        self.assertEqual(r, 0x42)

        mock.test_put_read_data(b'\x00\x10\x30\x00\x00\x31\x00')
        r = sot.read_packed('<HBI')
        self.assertEqual(r, (0x1000, 0x30, 0x310000))

    def test_peek(self):
        mock, sot = self.create_sot()

        mock.test_put_read_data(b'hello' + b'\x30\x40\x01\x10')

        r = sot.peek(5)
        self.assertEqual(r, b'hello')

        r = sot.read(5)
        self.assertEqual(r, b'hello')

        r = sot.peek_packed('<B')
        self.assertEqual(r, 0x30)

        r = sot.peek_packed('<BH')
        self.assertEqual(r, (0x30, 0x140))

        r = sot.read_packed('<H')
        self.assertEqual(r, 0x4030)

    def test_close(self):
        mock, sot = self.create_sot()

        sot.close()
        self.assertTrue(mock.test_closed)

    def test_cancel_read(self):
        mock, sot = self.create_sot()

        sot.cancel_read()
        self.assertTrue(mock.test_read_cancelled)
