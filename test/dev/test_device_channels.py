# pyshimmer - API for Shimmer sensor devices
# Copyright (C) 2023  Lukas Magel

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
from __future__ import annotations

from unittest import TestCase

import pytest

from pyshimmer.dev.channels import (
    ChannelDataType,
    EChannelType,
)


class EChannelTypeTest(TestCase):

    def test_channel_enum_uniqueness(self):
        try:
            # The exception will trigger upon import if the enum values are not unique
            from pyshimmer.dev.channels import EChannelType
        except ValueError as e:
            self.fail(f"Enum not unique: {e}")

    def test_e_channel_type(self):
        assert EChannelType.VBATT.value == 0x03
        assert EChannelType.VBATT.channel_id == 0x03
        assert EChannelType.VBATT.is_public

        assert EChannelType.TIMESTAMP.value == 0x100
        assert EChannelType.TIMESTAMP.channel_id == 0x100
        assert EChannelType.TIMESTAMP.is_public is False

    def test_channel_type_enum_for_id(self):
        assert EChannelType.enum_for_id(0x03) is EChannelType.VBATT

        with pytest.raises(ValueError):
            # Unknown ID
            EChannelType.enum_for_id(0x4242)

        with pytest.raises(ValueError):
            # Timestamp is not public
            EChannelType.enum_for_id(0x100)


class ESensorGroupTest:

    def test_sensor_group_uniqueness(self):
        try:
            # The exception will trigger upon import if the enum values are not unique
            from pyshimmer.dev.channels import ESensorGroup
        except ValueError as e:
            pytest.fail(f"Enum not unique: {e}")


class ChannelDataTypeTest(TestCase):

    def test_ch_dtype_byte_order(self):
        dtype = ChannelDataType(size=4, signed=True, le=True)
        assert dtype.byte_order == "little"

        dtype = ChannelDataType(size=4, signed=True, le=False)
        assert dtype.byte_order == "big"

    def test_channel_data_type_decoding(self):
        def test_both_endianess(byte_val_le: bytes, expected: int, signed: bool):
            blen = len(byte_val_le)
            dt_le = ChannelDataType(blen, signed=signed, le=True)
            dt_be = ChannelDataType(blen, signed=signed, le=False)

            self.assertEqual(expected, dt_le.decode(byte_val_le))
            self.assertEqual(expected, dt_be.decode(byte_val_le[::-1]))

        # Test the property getters
        dt = ChannelDataType(3, signed=False, le=True)
        self.assertEqual(dt.little_endian, True)
        self.assertEqual(dt.big_endian, False)
        self.assertEqual(dt.signed, False)
        self.assertEqual(dt.size, 3)

        # Test the property getters
        dt = ChannelDataType(3, signed=False, le=False)
        self.assertEqual(dt.little_endian, False)
        self.assertEqual(dt.big_endian, True)

        # Test unsigned decodation for 3 byte data
        test_both_endianess(b"\x00\x00\x00", 0x000000, signed=False)
        test_both_endianess(b"\x10\x00\x00", 0x000010, signed=False)
        test_both_endianess(b"\x00\x00\xff", 0xFF0000, signed=False)
        test_both_endianess(b"\xff\xff\xff", 0xFFFFFF, signed=False)

        # Test signed decodation for 3 byte data
        test_both_endianess(b"\xff\xff\xff", -1, signed=True)
        test_both_endianess(b"\x00\x00\x80", -(2**23), signed=True)
        test_both_endianess(b"\xff\xff\x7f", 2**23 - 1, signed=True)
        test_both_endianess(b"\xff\x00\x00", 255, signed=True)

        # Test unsigned decodation for 2 byte data
        test_both_endianess(b"\x00\x00", 0x0000, signed=False)
        test_both_endianess(b"\x10\x00", 0x0010, signed=False)
        test_both_endianess(b"\x00\xff", 0xFF00, signed=False)
        test_both_endianess(b"\xff\xff", 0xFFFF, signed=False)

        # Test signed decodation for 2 byte data
        test_both_endianess(b"\xff\xff", -1, signed=True)
        test_both_endianess(b"\x00\x80", -(2**15), signed=True)
        test_both_endianess(b"\xff\x7f", 2**15 - 1, signed=True)
        test_both_endianess(b"\xff\x00", 255, signed=True)

    def test_channel_data_type_encoding(self):
        def test_both_endianess(val: int, val_len: int, expected: bytes, signed: bool):
            dt_le = ChannelDataType(val_len, signed=signed, le=True)
            dt_be = ChannelDataType(val_len, signed=signed, le=False)

            self.assertEqual(expected, dt_le.encode(val))
            self.assertEqual(expected[::-1], dt_be.encode(val))

        test_both_endianess(0x1234, 2, b"\x34\x12", signed=False)
        test_both_endianess(-0x10, 2, b"\xf0\xff", signed=True)

        test_both_endianess(0x12345, 3, b"\x45\x23\x01", signed=False)
        test_both_endianess(-0x12345, 3, b"\xbb\xdc\xfe", signed=True)
