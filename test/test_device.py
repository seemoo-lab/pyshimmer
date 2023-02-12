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

import random
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
from unittest import TestCase

from pyshimmer.device import sr2dr, dr2sr, ChannelDataType, ChDataTypeAssignment, SensorChannelAssignment, \
    SensorBitAssignments, sec2ticks, ticks2sec, get_ch_dtypes, EChannelType, ExGRegister, ExGMux, get_firmware_type, \
    EFirmwareType, ExGRLDLead, ERLDRef, get_exg_ch, is_exg_ch, ESensorGroup, sensors2bitfield, bitfield2sensors, \
    sort_sensors


def randbytes(k: int) -> bytes:
    population = list(range(256))
    seq = random.choices(population, k=k)
    return bytes(seq)


class DeviceTest(TestCase):

    def setUp(self) -> None:
        random.seed(0x42)

    def test_channel_enum_uniqueness(self):
        try:
            # The exception will trigger upon import if the enum values are not unique
            from pyshimmer.device import EChannelType
        except ValueError as e:
            self.fail(f'Enum not unique: {e}')

    def test_sr2dr(self):
        r = sr2dr(1024.0)
        self.assertEqual(r, 32)

        r = sr2dr(500.0)
        self.assertEqual(r, 66)

    def test_dr2sr(self):
        r = dr2sr(65)
        self.assertEqual(round(r), 504)

        r = dr2sr(32)
        self.assertEqual(r, 1024.0)

        r = dr2sr(64)
        self.assertEqual(r, 512.0)

    def test_sec2ticks(self):
        r = sec2ticks(1.0)
        self.assertEqual(r, 32768)

    def test_ticks2sec(self):
        r = ticks2sec(32768)
        self.assertEqual(r, 1.0)

        r = ticks2sec(65536)
        self.assertEqual(r, 2.0)

    def test_channel_data_type(self):
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
            from pyshimmer.device import ESensorGroup
        except ValueError as e:
            self.fail(f'Enum not unique: {e}')

    def test_datatype_assignments(self):
        from pyshimmer.device import EChannelType
        for ch_type in EChannelType:
            if ch_type not in ChDataTypeAssignment:
                self.fail(f'No data type assigned to channel type: {ch_type}')

    def test_sensor_channel_assignments(self):
        from pyshimmer.device import ESensorGroup
        for sensor in ESensorGroup:
            if sensor not in SensorChannelAssignment:
                self.fail(f'No channels assigned to sensor type: {sensor}')

    def test_sensor_bit_assignments_uniqueness(self):
        for s1 in SensorBitAssignments.keys():
            for s2 in SensorBitAssignments.keys():
                if s1 != s2 and SensorBitAssignments[s1] == SensorBitAssignments[s2]:
                    self.fail(f'Colliding bitfield assignments for sensor {s1} and {s2}')

    def test_get_firmware_type(self):
        r = get_firmware_type(0x01)
        self.assertEqual(r, EFirmwareType.BtStream)
        r = get_firmware_type(0x02)
        self.assertEqual(r, EFirmwareType.SDLog)
        r = get_firmware_type(0x03)
        self.assertEqual(r, EFirmwareType.LogAndStream)

        self.assertRaises(ValueError, get_firmware_type, 0xFF)

    def test_get_exg_ch(self):
        self.assertEqual(get_exg_ch(EChannelType.EXG_ADS1292R_1_CH1_24BIT), (0, 0))
        self.assertEqual(get_exg_ch(EChannelType.EXG_ADS1292R_1_CH2_24BIT), (0, 1))
        self.assertEqual(get_exg_ch(EChannelType.EXG_ADS1292R_2_CH1_24BIT), (1, 0))
        self.assertEqual(get_exg_ch(EChannelType.EXG_ADS1292R_2_CH2_24BIT), (1, 1))

    def test_is_exg_ch(self):
        from itertools import product
        valid_ch = [EChannelType[f'EXG_ADS1292R_{i}_CH{j}_{k}BIT'] for i, j, k in product([1, 2], [1, 2], [16, 24])]

        for ch in EChannelType:
            self.assertEqual(is_exg_ch(ch), ch in valid_ch)

    def test_sensors2bitfield(self):
        sensors = [
            ESensorGroup.CH_A13,
            ESensorGroup.GYRO,
            ESensorGroup.PRESSURE
        ]
        bitfield = sensors2bitfield(sensors)
        self.assertEqual(bitfield, 0x040140)

    def test_bitfield2sensors(self):
        expected = [
            ESensorGroup.CH_A13,
            ESensorGroup.GYRO,
            ESensorGroup.PRESSURE
        ]

        bitfield = 0x040140
        actual = bitfield2sensors(bitfield)
        self.assertEqual(expected, actual)

    def test_sort_sensors(self):
        sensors = [ESensorGroup.BATTERY, ESensorGroup.ACCEL_LN]
        expected = [ESensorGroup.ACCEL_LN, ESensorGroup.BATTERY]
        r = sort_sensors(sensors)
        self.assertEqual(r, expected)

        sensors = [ESensorGroup.CH_A15, ESensorGroup.MAG_MPU, ESensorGroup.ACCEL_LN, ESensorGroup.CH_A15]
        expected = [ESensorGroup.ACCEL_LN, ESensorGroup.CH_A15, ESensorGroup.CH_A15, ESensorGroup.MAG_MPU]
        r = sort_sensors(sensors)
        self.assertEqual(r, expected)


class ExGRegisterTest(TestCase):

    def test_exg_register_fail(self):
        self.assertRaises(ValueError, ExGRegister, bytes())

    def test_exg_register(self):
        reg1 = bytes([3, 160, 16, 64, 71, 0, 0, 0, 2, 1])
        reg2 = bytes([0, 171, 16, 21, 21, 0, 0, 0, 2, 1])

        exg_reg1 = ExGRegister(reg1)
        exg_reg2 = ExGRegister(reg2)

        self.assertEqual(exg_reg1.ch1_gain, 4)
        self.assertEqual(exg_reg1.ch2_gain, 4)
        self.assertEqual(exg_reg1.ch1_mux, ExGMux.NORMAL)
        self.assertEqual(exg_reg1.get_ch_mux_bin(0), 0b0000)
        self.assertEqual(exg_reg1.ch2_mux, ExGMux.RLD_DRM)
        self.assertEqual(exg_reg1.get_ch_mux_bin(1), 0b0111)
        self.assertEqual(exg_reg1.ch1_powerdown, False)
        self.assertEqual(exg_reg1.ch2_powerdown, False)
        self.assertEqual(exg_reg1.data_rate, 1000)
        self.assertEqual(exg_reg1.binary, reg1)

        self.assertEqual(exg_reg2.ch1_gain, 1)
        self.assertEqual(exg_reg2.ch2_gain, 1)
        self.assertEqual(exg_reg2.ch1_mux, ExGMux.TEST_SIGNAL)
        self.assertEqual(exg_reg2.ch2_mux, ExGMux.TEST_SIGNAL)
        self.assertEqual(exg_reg2.ch1_powerdown, False)
        self.assertEqual(exg_reg2.ch2_powerdown, False)
        self.assertEqual(exg_reg2.data_rate, 125)
        self.assertEqual(exg_reg2.binary, reg2)

        self.assertRaises(ValueError, exg_reg1.get_ch_mux, 2)
        self.assertRaises(ValueError, exg_reg1.get_ch_mux, -1)

    def test_exg_register_powerdown(self):
        pd = 0x1 << 7
        reg_bin = bytes([3, 160, 16, pd, pd, 0, 0, 0, 2, 1])
        reg = ExGRegister(reg_bin)

        self.assertEqual(reg.ch1_powerdown, True)
        self.assertEqual(reg.ch2_powerdown, True)

    def test_exg_register_rld_powerdown(self):
        pd = 0x01 << 5
        reg_bin = bytes([0, 0, 0, 0, 0, pd, 0, 0, 0, 0])
        reg = ExGRegister(reg_bin)

        self.assertEqual(reg.rld_powerdown, False)

    def test_exg_register_rld_channels(self):
        reg_bin = bytes([0x03, 0xA8, 0x10, 0x40, 0x40, 0x2D, 0x00, 0x00, 0x02, 0x03])
        reg = ExGRegister(reg_bin)
        self.assertEqual(reg.rld_channels, [ExGRLDLead.RLD1P, ExGRLDLead.RLD2P, ExGRLDLead.RLD2N])

        reg_bin = bytes([0x03, 0xA8, 0x10, 0x40, 0x40, 0x00, 0x00, 0x00, 0x02, 0x03])
        reg = ExGRegister(reg_bin)
        self.assertEqual(reg.rld_channels, [])

    def test_exg_register_rld_ref(self):
        reg_bin = bytes([0x03, 0xA8, 0x10, 0x40, 0x40, 0x2D, 0x00, 0x00, 0x02, 0x03])
        reg = ExGRegister(reg_bin)
        self.assertEqual(reg.rld_ref, ERLDRef.INTERNAL)

        reg_bin = bytes([0x03, 0xA8, 0x10, 0x40, 0x40, 0x2D, 0x00, 0x00, 0x02, 0x01])
        reg = ExGRegister(reg_bin)
        self.assertEqual(reg.rld_ref, ERLDRef.EXTERNAL)

    def test_exg_register_print(self):
        reg_bin = bytes([0x03, 0xA8, 0x10, 0x40, 0x40, 0x2D, 0x00, 0x00, 0x02, 0x03])
        reg = ExGRegister(reg_bin)

        str_repr = str(reg)
        self.assertTrue('Data Rate: 1000' in str_repr)
        self.assertTrue('RLD Powerdown: False' in str_repr)

    def test_equality_operator(self):
        def do_assert(a: bytes, b: bytes, result: bool) -> None:
            self.assertEqual(ExGRegister(a) == ExGRegister(b), result)

        x = randbytes(10)
        y = randbytes(10)

        do_assert(x, y, False)
        do_assert(x, x, True)
        do_assert(y, y, True)

        for i in range(len(x)):
            y = bytearray(x)
            y[i] = random.randrange(0, 256)
            do_assert(x, y, False)
