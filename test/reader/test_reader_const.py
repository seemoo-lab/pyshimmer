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

from pyshimmer.dev.channels import ESensorGroup
from pyshimmer.reader.reader_const import sort_sensors


class ReaderConstTest(TestCase):

    def test_sort_sensors(self):
        sensors = [ESensorGroup.BATTERY, ESensorGroup.ACCEL_LN]
        expected = [ESensorGroup.ACCEL_LN, ESensorGroup.BATTERY]
        r = sort_sensors(sensors)
        self.assertEqual(r, expected)

        sensors = [ESensorGroup.CH_A15, ESensorGroup.MAG_MPU, ESensorGroup.ACCEL_LN, ESensorGroup.CH_A15]
        expected = [ESensorGroup.ACCEL_LN, ESensorGroup.CH_A15, ESensorGroup.CH_A15, ESensorGroup.MAG_MPU]
        r = sort_sensors(sensors)
        self.assertEqual(r, expected)
