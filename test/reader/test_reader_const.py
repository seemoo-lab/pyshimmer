from unittest import TestCase

from pyshimmer.device import ESensorGroup
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
