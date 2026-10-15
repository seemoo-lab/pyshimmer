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

from pyshimmer.dev.fw_version import (
    FirmwareVersion,
    FirmwareType,
    FirmwareCapabilities,
)
from pyshimmer.dev.revisions import RevisionRegistry


class TestFirmwareType:

    def tet_firmware_type(self):
        r = FirmwareType.from_int(0x01)
        assert r == FirmwareType.BtStream
        r = FirmwareType.from_int(0x02)
        assert r == FirmwareType.SDLog
        r = FirmwareType.from_int(0x03)
        assert r == FirmwareType.LogAndStream

        r = FirmwareType.from_int(100)
        assert r == FirmwareType.Unknown


class FirmwareCapabilitiesTest(TestCase):

    def test_capabilities(self):
        revision = RevisionRegistry.REV_SHIMMER3
        cap = FirmwareCapabilities(
            revision, FirmwareType.LogAndStream, version=FirmwareVersion(1, 2, 3)
        )
        self.assertTrue(cap.supports_ack_disable)
        self.assertEqual(cap.version, FirmwareVersion(1, 2, 3))
        self.assertEqual(cap.fw_type, FirmwareType.LogAndStream)

    def test_status_byte_count(self):
        rev3 = RevisionRegistry.REV_SHIMMER3
        rev3r = RevisionRegistry.REV_SHIMMER3R
        las = FirmwareType.LogAndStream
        cases = [
            # Shimmer3R LogAndStream adds the USB plugged-in state from v1.0.24
            (rev3r, las, (1, 0, 24), 2),
            (rev3r, las, (1, 1, 0), 2),
            (rev3r, las, (2, 0, 0), 2),
            (rev3r, las, (1, 0, 23), 1),
            (rev3r, las, (0, 0, 2), 1),
            (rev3r, FirmwareType.SDLog, (1, 0, 24), 1),
            (rev3r, FirmwareType.BtStream, (1, 0, 24), 1),
            (rev3r, FirmwareType.Unknown, (1, 0, 24), 1),
            # Shimmer3 version numbers overlap, but no Shimmer3 firmware sends it
            (rev3, las, (1, 0, 24), 1),
            (rev3, las, (0, 16, 0), 1),
        ]
        for rev, fw_type, version, expected in cases:
            with self.subTest(rev=rev.hardware_version, fw_type=fw_type, v=version):
                cap = FirmwareCapabilities(rev, fw_type, FirmwareVersion(*version))
                self.assertEqual(cap.status_byte_count, expected)


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
