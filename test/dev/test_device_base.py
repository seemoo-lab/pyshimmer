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

from pyshimmer.dev.base import sr2dr, dr2sr, sec2ticks, ticks2sec


class DeviceBaseTest(TestCase):

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
