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
import random
from unittest import TestCase

from pyshimmer.dev.channels import EChannelType
from pyshimmer.dev.exg import is_exg_ch, get_exg_ch, ExGMux, ExGRLDLead, ERLDRef, ExGRegister


def randbytes(k: int) -> bytes:
    population = list(range(256))
    seq = random.choices(population, k=k)
    return bytes(seq)


class DeviceExGTest(TestCase):

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


class ExGRegisterTest(TestCase):

    def setUp(self) -> None:
        random.seed(0x42)

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
