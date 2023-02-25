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

from pyshimmer.dev.fw_version import FirmwareVersion, get_firmware_type, EFirmwareType


class DeviceFirmwareVersionTest(TestCase):

    def test_get_firmware_type(self):
        r = get_firmware_type(0x01)
        self.assertEqual(r, EFirmwareType.BtStream)
        r = get_firmware_type(0x02)
        self.assertEqual(r, EFirmwareType.SDLog)
        r = get_firmware_type(0x03)
        self.assertEqual(r, EFirmwareType.LogAndStream)

        self.assertRaises(ValueError, get_firmware_type, 0xFF)


class FirmwareVersionTest(TestCase):

    def test_version_equality(self):
        a = FirmwareVersion(1, 2, 3)
        b = FirmwareVersion(1, 2, 3)
        c = FirmwareVersion(3, 2, 1)

        self.assertEqual(a, a)
        self.assertEqual(a, b)

        self.assertNotEqual(a, None)
        self.assertNotEqual(a, False)
        self.assertNotEqual(a, 10)
        self.assertNotEqual(a, c)

    def test_attributes(self):
        ver = FirmwareVersion(1, 2, 3)
        self.assertEqual(ver.major, 1)
        self.assertEqual(ver.minor, 2)
        self.assertEqual(ver.rel, 3)

    def test_greater_less(self):
        a = FirmwareVersion(3, 2, 1)

        b = FirmwareVersion(3, 2, 1)
        self.assertFalse(b > a)
        self.assertTrue(b >= a)
        self.assertFalse(b < a)
        self.assertTrue(b <= a)

        b = FirmwareVersion(2, 2, 1)
        self.assertFalse(b > a)
        self.assertFalse(b >= a)
        self.assertTrue(b < a)
        self.assertTrue(b <= a)

        b = FirmwareVersion(3, 1, 1)
        self.assertFalse(b > a)
        self.assertFalse(b >= a)
        self.assertTrue(b < a)
        self.assertTrue(b <= a)

        b = FirmwareVersion(3, 2, 0)
        self.assertFalse(b > a)
        self.assertFalse(b >= a)
        self.assertTrue(b < a)
        self.assertTrue(b <= a)
