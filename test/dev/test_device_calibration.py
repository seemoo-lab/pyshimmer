# pyshimmer - API for Shimmer sensor devices
# Copyright (C) 2023  Lukas Magel, Manuel Fernandez-Carmona

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
from pyshimmer.dev.calibration import AllCalibration

def randbytes(k: int) -> bytes:
    population = list(range(256))
    seq = random.choices(population, k=k)
    return bytes(seq)

class AllCalibrationTest(TestCase):

    def test_equality_operator(self):
        def do_assert(a: bytes, b: bytes, result: bool) -> None:
            self.assertEqual(AllCalibration(a) == AllCalibration(b), result)

        x = randbytes(84)
        y = randbytes(84)

        do_assert(x, y, False)
        do_assert(x, x, True)
        do_assert(y, y, True)

        for i in range(len(x)):
            y = bytearray(x)
            y[i] = random.randrange(0, 256)
            do_assert(x, y, False)

    def setUp(self) -> None:
        random.seed(0x42)

    def test_allcalibration_fail(self):
        self.assertRaises(ValueError, AllCalibration, bytes())

    def test_allcalibration(self):
        bin_reg1 = bytes([0x08, 0xcd, 0x08, 0xcd, 0x08, 0xcd, 0x00, 0x5c, 0x00, 0x5c, 
                          0x00, 0x5c, 0x00, 0x9c, 0x00, 0x9c, 0x00, 0x00, 0x00, 0x00, 
                          0x9c, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x19, 0x96, 0x19, 
                          0x96, 0x19, 0x96, 0x00, 0x9c, 0x00, 0x9c, 0x00, 0x00, 0x00, 
                          0x00, 0x9c, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x02, 0x9b, 
                          0x02, 0x9b, 0x02, 0x9b, 0x00, 0x9c, 0x00, 0x64, 0x00, 0x00, 
                          0x00, 0x00, 0x9c, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x06, 
                          0x87, 0x06, 0x87, 0x06, 0x87, 0x00, 0x9c, 0x00, 0x64, 0x00, 
                          0x00, 0x00, 0x00, 0x9c])

        bin_reg2 = bytes([0x08, 0xcd, 0x08, 0xcd, 0x08, 0xcd, 0x00, 0x5c, 0x00, 0x5c, 
                          0x00, 0x5c, 0x00, 0x9c, 0x00, 0x9c, 0x00, 0x00, 0x00, 0x00, 
                          0x9c, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x19, 0x96, 0x19, 
                          0x96, 0x19, 0x96, 0x00, 0x9c, 0x00, 0x9c, 0x00, 0x00, 0x00, 
                          0x00, 0x9c, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
                          0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
                          0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x06, 
                          0x87, 0x06, 0x87, 0x06, 0x87, 0x00, 0x9c, 0x00, 0x64, 0x00, 
                          0x00, 0x00, 0x00, 0x9c])

        allcalib1 = AllCalibration(bin_reg1)
        allcalib2 = AllCalibration(bin_reg2)
        self.assertEqual(allcalib1.get_offset_bias(0), [2253, 2253, 2253] )
        self.assertEqual(allcalib1.get_sensitivity(0), [92, 92, 92] )
        self.assertEqual(allcalib1.get_ali_mat(0),     [0, -100, 0, -100, 0, 0, 0, 0, -100] )
        self.assertEqual(allcalib1.get_offset_bias(1), [0, 0, 0] )
        self.assertEqual(allcalib1.get_sensitivity(1), [6550, 6550, 6550] )
        self.assertEqual(allcalib1.get_ali_mat(1),     [0, -100, 0, -100, 0, 0, 0, 0, -100] )
        self.assertEqual(allcalib1.get_offset_bias(2), [0, 0, 0] )
        self.assertEqual(allcalib1.get_sensitivity(2), [667, 667, 667] )
        self.assertEqual(allcalib1.get_ali_mat(2),     [0, -100, 0, 100, 0, 0, 0, 0, -100] )
        self.assertEqual(allcalib1.get_offset_bias(3), [0, 0, 0] )
        self.assertEqual(allcalib1.get_sensitivity(3), [1671, 1671, 1671] )
        self.assertEqual(allcalib1.get_ali_mat(3),     [0, -100, 0, 100, 0, 0, 0, 0, -100] )
        
        self.assertEqual(allcalib2.get_offset_bias(0), [2253, 2253, 2253])
        self.assertEqual(allcalib2.get_sensitivity(0), [92, 92, 92])
        self.assertEqual(allcalib2.get_ali_mat(0),     [0, -100, 0, -100, 0, 0, 0, 0, -100])
        self.assertEqual(allcalib2.get_offset_bias(1), [0, 0, 0])
        self.assertEqual(allcalib2.get_sensitivity(1), [6550, 6550, 6550])
        self.assertEqual(allcalib2.get_ali_mat(1),     [0, -100, 0, -100, 0, 0, 0, 0, -100])
        self.assertEqual(allcalib2.get_offset_bias(2), [0, 0, 0])
        self.assertEqual(allcalib2.get_sensitivity(2), [0, 0, 0])
        self.assertEqual(allcalib2.get_ali_mat(2),     [0, 0, 0, 0, 0, 0, 0, 0, 0])
        self.assertEqual(allcalib2.get_offset_bias(3), [0, 0, 0])
        self.assertEqual(allcalib2.get_sensitivity(3), [1671, 1671, 1671])
        self.assertEqual(allcalib2.get_ali_mat(3),     [0, -100, 0, 100, 0, 0, 0, 0, -100])

    def test_exg_register_print(self):
        bin_reg = bytes([0x08, 0xcd, 0x08, 0xcd, 0x08, 0xcd, 0x00, 0x5c, 0x00, 0x5c, 
                         0x00, 0x5c, 0x00, 0x9c, 0x00, 0x9c, 0x00, 0x00, 0x00, 0x00, 
                         0x9c, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x19, 0x96, 0x19, 
                         0x96, 0x19, 0x96, 0x00, 0x9c, 0x00, 0x9c, 0x00, 0x00, 0x00, 
                         0x00, 0x9c, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
                         0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
                         0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x06, 
                         0x87, 0x06, 0x87, 0x06, 0x87, 0x00, 0x9c, 0x00, 0x64, 0x00, 
                         0x00, 0x00, 0x00, 0x9c])

        allcalib = AllCalibration(bin_reg)

        str_repr = str(allcalib)
        self.assertTrue('Offset bias: [0, 0, 0]' in str_repr)
        self.assertTrue('Sensitivity: [1671,' in str_repr)

