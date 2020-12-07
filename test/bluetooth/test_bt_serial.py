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
from typing import Tuple
from unittest import TestCase

from pyshimmer.bluetooth.bt_serial import BluetoothSerial
from pyshimmer.test_util import MockSerial


class BluetoothSerialTest(TestCase):

    @staticmethod
    def create_sot() -> Tuple[MockSerial, BluetoothSerial]:
        mock = MockSerial()
        # noinspection PyTypeChecker
        serial = BluetoothSerial(mock)
        return mock, serial

    def test_read_varlen(self):
        mock, sot = self.create_sot()

        mock.test_put_read_data(b'\x00\x04\x01\x02\x03\x04')
        r = sot.read_varlen()
        self.assertEqual(r, b'')

        r = sot.read_varlen()
        self.assertEqual(r, b'\x01\x02\x03\x04')

    def test_write_varlen(self):
        mock, sot = self.create_sot()

        sot.write_varlen(b'thisisatest')
        r = mock.test_get_write_data()

        self.assertEqual(r[0], 11)
        self.assertEqual(r[1:], b'thisisatest')

        self.assertRaises(ValueError, sot.write_varlen, b'A' * 300)

    def test_write_command(self):
        mock, sot = self.create_sot()

        sot.write_command(0x10, '>BH', 0x42, 0x10)
        r = mock.test_get_write_data()
        self.assertEqual(r, b'\x10\x42\x00\x10')

        sot.write_command(0x11, 'varlen', b'hello')
        r = mock.test_get_write_data()
        self.assertEqual(r, b'\x11\x05hello')

    def test_read_ack(self):
        mock, sot = self.create_sot()
        mock.test_put_read_data(b'\xFF\x00')

        sot.read_ack()
        self.assertRaises(ValueError, sot.read_ack)

    def test_read_response(self):
        mock, sot = self.create_sot()

        # int response code
        mock.test_put_read_data(b'\x42')
        r = sot.read_response(0x42)
        self.assertEqual(r, ())

        mock.test_clear_read_buffer()
        mock.test_put_read_data(b'\x42')
        self.assertRaises(RuntimeError, sot.read_response, 0x43)

        # Single-byte tuple response code
        mock.test_clear_read_buffer()
        mock.test_put_read_data(b'\x42')
        r = sot.read_response((0x42,))
        self.assertEqual(r, ())

        mock.test_clear_read_buffer()
        mock.test_put_read_data(b'\x42')
        self.assertRaises(RuntimeError, sot.read_response, (0x43,))

        # Multi-byte tuple response code
        mock.test_clear_read_buffer()
        mock.test_put_read_data(b'\x42\x43')
        r = sot.read_response((0x42, 0x43))
        self.assertEqual(r, ())

        mock.test_clear_read_buffer()
        mock.test_put_read_data(b'\x43\x42')
        self.assertRaises(RuntimeError, sot.read_response, (0x43, 0x44))

        # bytes response code
        mock.test_clear_read_buffer()
        mock.test_put_read_data(b'\x42\x43')
        r = sot.read_response(b'\x42\x43')
        self.assertEqual(r, ())

        mock.test_clear_read_buffer()
        mock.test_put_read_data(b'\x42\x44')
        self.assertRaises(RuntimeError, sot.read_response, b'\x43\x44')

        mock.test_clear_read_buffer()
        mock.test_put_read_data(b'\x50\x03\x00\x01\x02')
        r = sot.read_response(0x50, arg_format='varlen')
        self.assertEqual(r, b'\x00\x01\x02')

        mock.test_clear_read_buffer()
        mock.test_put_read_data(b'\x50\x03\x00\x01\x02')
        r = sot.read_response(0x50, arg_format='<HBB')
        self.assertEqual(r, (0x3, 0x1, 0x2))
