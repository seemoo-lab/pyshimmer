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
from unittest import TestCase
from pyshimmer.util import PeekQueue

import numpy as np

from unittest.mock import Mock

from io import BytesIO
from pyshimmer.util import bit_is_set, raise_to_next_pow, flatten_list, fmt_hex, unpack, unwrap, calibrate_u12_adc_value, battery_voltage_to_percent, \
     FileIOBase


class UtilTest(TestCase):

    def test_bit_is_set(self):
        r = bit_is_set(0x10, 0x01)
        self.assertEqual(r, False)

        r = bit_is_set(0x10, 0x10)
        self.assertEqual(r, True)

        r = bit_is_set(0x05, 0x01)
        self.assertEqual(r, True)

        r = bit_is_set(0x05, 0x02)
        self.assertEqual(r, False)

        r = bit_is_set(0x05, 0x04)
        self.assertEqual(r, True)

    def test_raise_to_next_pow(self):
        r = raise_to_next_pow(0)
        self.assertEqual(r, 1)

        r = raise_to_next_pow(1)
        self.assertEqual(r, 1)

        r = raise_to_next_pow(2)
        self.assertEqual(r, 2)

        r = raise_to_next_pow(3)
        self.assertEqual(r, 4)

        r = raise_to_next_pow(4)
        self.assertEqual(r, 4)

        r = raise_to_next_pow(6)
        self.assertEqual(r, 8)

        r = raise_to_next_pow(14)
        self.assertEqual(r, 16)

    def test_flatten_list(self):
        r = flatten_list([[10], [20]])
        self.assertEqual(r, [10, 20])

        r = flatten_list(((10,), (20,)))
        self.assertEqual(r, [10, 20])

        r = flatten_list([[10]])
        self.assertEqual(r, [10])

    def test_fmt_hex(self):
        r = fmt_hex(b'\x01')
        self.assertEqual(r, '01')

        r = fmt_hex(b'\x01\x02')
        self.assertEqual(r, '01 02')

    def test_unpack(self):
        r = unpack([10])

        self.assertEqual(r, 10)

        r = unpack([10, 20])
        self.assertEqual(r, [10, 20])

        r = unpack([])
        self.assertEqual(r, [])

        r = unpack(())
        self.assertEqual(r, ())

        r = unpack((10,))
        self.assertEqual(r, 10)

        r = unpack((10, 20))
        self.assertEqual(r, (10, 20))

    # noinspection PyMethodMayBeStatic
    def test_unwrap(self):
        shift = 10
        x = np.array([0, 1, 5, 8, 0, 2, 5, 10, 3, 7, 9])
        e = np.array([0, 1, 5, 8, 10, 12, 15, 20, 23, 27, 29])

        r = unwrap(x, shift)
        np.testing.assert_equal(r, e)

        x = np.array([0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2])
        e = np.array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14])

        r = unwrap(x, 4)
        np.testing.assert_equal(r, e)

        e = np.arange(0, 2000, 45)
        x = e % 250

        r = unwrap(x, 250)
        np.testing.assert_equal(r, e)

        e = np.arange(0, 4 * (2 ** 24), 65)
        x = e % (2 ** 24)

        r = unwrap(x, 2 ** 24)
        np.testing.assert_equal(r, e)

    def test_calibrate_u12_adc_value(self):
        uncalibratedData = 2863
        offset = 0
        vRefP = 3.0
        gain = 1.0
        
        actual = calibrate_u12_adc_value(uncalibratedData, offset, vRefP, gain)

        desired = 2.0974358974358975
        np.testing.assert_almost_equal(actual, desired)

    def test_battery_voltage_to_percent(self):
        voltage = 3.9078
        desired = 72.8

        actual = battery_voltage_to_percent(voltage)
        np.testing.assert_equal(actual, desired)

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

    def test_file_io_base(self):
        input_bin = bytes(range(255))
        io_obj = BytesIO(input_bin)

        sut = FileIOBase(io_obj)
        self.assertEqual(sut._tell(), 0)

        sut._seek(10)
        self.assertEqual(sut._tell(), 10)

        sut._seek_relative(-2)
        self.assertEqual(sut._tell(), 8)

        r = sut._read(2)
        self.assertEqual(r, b'\x08\x09')

        r = sut._read_packed('<H')
        self.assertEqual(r, 0x0B0A)

    def test_file_io_base_not_seekable(self):
        mock = Mock(spec=BytesIO)
        mock.seekable.return_value = False

        self.assertRaises(ValueError, FileIOBase, mock)
