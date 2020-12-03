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

from pyshimmer.test_util import MockSerial
from pyshimmer.uart.dock_serial import DockSerial, generate_crc


class CRCCalculationTest(TestCase):

    def test_generate_crc_uneven(self):
        crc_init = 0xB0CA
        msg = b'\x24\x03\x02\x01\x03'
        exp_crc = b'\xca\xdc'

        act_crc = generate_crc(msg, crc_init)
        self.assertEqual(act_crc, exp_crc)

    def test_generate_crc_even(self):
        crc_init = 0xB0CA
        msg = b'\x24\x03\x02\x01'
        exp_crc = b'\x4b\xc2'

        act_crc = generate_crc(msg, crc_init)
        print(act_crc)
        self.assertEqual(act_crc, exp_crc)


class DockSerialTest(TestCase):

    @staticmethod
    def create_sot(crc_init: int = 10) -> Tuple[DockSerial, MockSerial]:
        mock = MockSerial()
        # noinspection PyTypeChecker
        serial = DockSerial(mock, crc_init=crc_init)
        return serial, mock

    def test_read(self):
        crc_init = 42
        serial, mock = self.create_sot(crc_init)

        data_no_verify = b'abcd'
        data = b'\x01\x02\x03\x04'
        crc = generate_crc(data, crc_init)
        mock.test_put_read_data(data_no_verify + data + crc)

        r = serial.read(4)
        self.assertEqual(data_no_verify, r)

        serial.start_read_crc_verify()
        r = serial.read(4)
        serial.end_read_crc_verify()

        self.assertEqual(data, r)
        self.assertEqual(mock.test_get_remaining_read_data(), b'')

        mock.reset_input_buffer()
        mock.test_put_read_data(data + b'\x00\x01')

        serial.start_read_crc_verify()
        r = serial.read(4)
        self.assertEqual(r, data)
        self.assertRaises(IOError, serial.end_read_crc_verify)

    def test_write(self):
        crc_init = 42
        serial, mock = self.create_sot(crc_init)

        data_no_verify = b'1234'
        data = b'another test'
        crc = generate_crc(data, crc_init)

        serial.write(data_no_verify)

        serial.start_write_crc()
        serial.write(data)
        serial.end_write_crc()

        r = mock.test_get_write_data()
        self.assertEqual(len(r), 18)
        self.assertEqual(r[:4], b'1234')
        self.assertEqual(r[4:16], b'another test')
        self.assertEqual(r[-2:], crc)
