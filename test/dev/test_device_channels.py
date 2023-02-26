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
from unittest import TestCase

from pyshimmer.dev.channels import ChDataTypeAssignment, get_ch_dtypes, SensorChannelAssignment, SensorBitAssignments, \
    ChannelDataType, EChannelType, ESensorGroup, sort_sensors


class DeviceChannelsTest(TestCase):

    def test_channel_enum_uniqueness(self):
        try:
            # The exception will trigger upon import if the enum values are not unique
            from pyshimmer.dev.channels import EChannelType
        except ValueError as e:
            self.fail(f'Enum not unique: {e}')

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
        test_both_endianess(b'\x00\x00\x00', 0x000000, signed=False)
        test_both_endianess(b'\x10\x00\x00', 0x000010, signed=False)
        test_both_endianess(b'\x00\x00\xFF', 0xFF0000, signed=False)
        test_both_endianess(b'\xFF\xFF\xFF', 0xFFFFFF, signed=False)

        # Test signed decodation for 3 byte data
        test_both_endianess(b'\xFF\xFF\xFF', -1, signed=True)
        test_both_endianess(b'\x00\x00\x80', -2 ** 23, signed=True)
        test_both_endianess(b'\xFF\xFF\x7F', 2 ** 23 - 1, signed=True)
        test_both_endianess(b'\xFF\x00\x00', 255, signed=True)

        # Test unsigned decodation for 2 byte data
        test_both_endianess(b'\x00\x00', 0x0000, signed=False)
        test_both_endianess(b'\x10\x00', 0x0010, signed=False)
        test_both_endianess(b'\x00\xFF', 0xFF00, signed=False)
        test_both_endianess(b'\xFF\xFF', 0xFFFF, signed=False)

        # Test signed decodation for 2 byte data
        test_both_endianess(b'\xFF\xFF', -1, signed=True)
        test_both_endianess(b'\x00\x80', -2 ** 15, signed=True)
        test_both_endianess(b'\xFF\x7F', 2 ** 15 - 1, signed=True)
        test_both_endianess(b'\xFF\x00', 255, signed=True)

    def test_channel_data_type_encoding(self):
        def test_both_endianess(val: int, val_len: int, expected: bytes, signed: bool):
            dt_le = ChannelDataType(val_len, signed=signed, le=True)
            dt_be = ChannelDataType(val_len, signed=signed, le=False)

            self.assertEqual(expected, dt_le.encode(val))
            self.assertEqual(expected[::-1], dt_be.encode(val))

        test_both_endianess(0x1234, 2, b'\x34\x12', signed=False)
        test_both_endianess(-0x10, 2, b'\xF0\xFF', signed=True)

        test_both_endianess(0x12345, 3, b'\x45\x23\x01', signed=False)
        test_both_endianess(-0x12345, 3, b'\xbb\xdc\xfe', signed=True)

    def test_get_ch_dtypes(self):
        channels = [EChannelType.INTERNAL_ADC_13, EChannelType.GYRO_MPU9150_Y]
        r = get_ch_dtypes(channels)

        self.assertEqual(len(r), 2)
        first, second = r

        self.assertEqual(first.size, 2)
        self.assertEqual(first.little_endian, True)
        self.assertEqual(first.signed, False)

        self.assertEqual(second.size, 2)
        self.assertEqual(second.little_endian, False)
        self.assertEqual(second.signed, True)

    def test_sensor_group_uniqueness(self):
        try:
            # The exception will trigger upon import if the enum values are not unique
            from pyshimmer.dev.channels import ESensorGroup
        except ValueError as e:
            self.fail(f'Enum not unique: {e}')

    def test_datatype_assignments(self):
        from pyshimmer.dev.channels import EChannelType
        for ch_type in EChannelType:
            if ch_type not in ChDataTypeAssignment:
                self.fail(f'No data type assigned to channel type: {ch_type}')

    def test_sensor_channel_assignments(self):
        from pyshimmer.dev.channels import ESensorGroup
        for sensor in ESensorGroup:
            if sensor not in SensorChannelAssignment:
                self.fail(f'No channels assigned to sensor type: {sensor}')

    def test_sensor_bit_assignments_uniqueness(self):
        for s1 in SensorBitAssignments.keys():
            for s2 in SensorBitAssignments.keys():
                if s1 != s2 and SensorBitAssignments[s1] == SensorBitAssignments[s2]:
                    self.fail(f'Colliding bitfield assignments for sensor {s1} and {s2}')

    def test_sort_sensors(self):
        sensors = [ESensorGroup.BATTERY, ESensorGroup.ACCEL_LN]
        expected = [ESensorGroup.ACCEL_LN, ESensorGroup.BATTERY]
        r = sort_sensors(sensors)
        self.assertEqual(r, expected)

        sensors = [ESensorGroup.CH_A15, ESensorGroup.MAG_MPU, ESensorGroup.ACCEL_LN, ESensorGroup.CH_A15]
        expected = [ESensorGroup.ACCEL_LN, ESensorGroup.CH_A15, ESensorGroup.CH_A15, ESensorGroup.MAG_MPU]
        r = sort_sensors(sensors)
        self.assertEqual(r, expected)
