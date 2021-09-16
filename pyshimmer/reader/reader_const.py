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
from typing import Dict, List

from pyshimmer.device import ESensorGroup

SR_OFFSET = 0x00

ENABLED_SENSORS_OFFSET = 0x03
ENABLED_SENSORS_LEN = 0x03

RTC_CLOCK_DIFF_OFFSET = 0x2C

START_TS_OFFSET = 0xFB
START_TS_LEN = 0x5

TRIAL_CONFIG_OFFSET = 0x10

DATA_LOG_OFFSET = 0x100
BLOCK_LEN = 0x200

TRIAL_CONFIG_SYNC = 0x04 << 8 * 0
TRIAL_CONFIG_MASTER = 0x02 << 8 * 0

EXG_REG_OFFSET = 0x38
EXG_REG_LEN = 0x0A

# The file offsets at which the calibration parameters of the respective sensor can be found
TRIAXCAL_FILE_OFFSET = {
    ESensorGroup.ACCEL_LN: 0x8B,
    ESensorGroup.ACCEL_WR: 0x4C,
    ESensorGroup.GYRO: 0x61,
    ESensorGroup.MAG: 0x76,
}

# Scaling value by which the calibration offset will be scaled upon deserialization
TRIAXCAL_OFFSET_SCALING = {
    ESensorGroup.ACCEL_LN: 1.0,
    ESensorGroup.ACCEL_WR: 1.0,
    ESensorGroup.GYRO: 1.0,
    ESensorGroup.MAG: 1.0,
}

# Scaling value by which the calibration gain will be scaled upon deserialization
TRIAXCAL_GAIN_SCALING = {
    ESensorGroup.ACCEL_LN: 1.0,
    ESensorGroup.ACCEL_WR: 1.0,
    ESensorGroup.GYRO: 1.0 / 100.0,
    ESensorGroup.MAG: 1.0,
}

# Scaling value by which the calibration alignment matrix will be scaled upon deserialization
TRIAXCAL_ALIGNMENT_SCALING = {
    ESensorGroup.ACCEL_LN: 1.0 / 100.0,
    ESensorGroup.ACCEL_WR: 1.0 / 100.0,
    ESensorGroup.GYRO: 1.0 / 100.0,
    ESensorGroup.MAG: 1.0 / 100.0,
}

TRIAXCAL_SENSORS = list(TRIAXCAL_FILE_OFFSET.keys())

SensorOrder: Dict[ESensorGroup, int] = {
    ESensorGroup.ACCEL_LN: 1,
    ESensorGroup.BATTERY: 2,
    ESensorGroup.CH_A7: 3,
    ESensorGroup.CH_A6: 4,
    ESensorGroup.CH_A15: 5,
    ESensorGroup.CH_A12: 6,
    ESensorGroup.CH_A13: 7,
    ESensorGroup.CH_A14: 8,
    ESensorGroup.STRAIN: 9,
    ESensorGroup.CH_A1: 10,
    ESensorGroup.GSR: 11,
    ESensorGroup.GYRO: 12,
    ESensorGroup.ACCEL_WR: 13,
    ESensorGroup.MAG: 14,
    ESensorGroup.ACCEL_MPU: 15,
    ESensorGroup.MAG_MPU: 16,
    ESensorGroup.PRESSURE: 17,
    ESensorGroup.EXG1_24BIT: 18,
    ESensorGroup.EXG1_16BIT: 19,
    ESensorGroup.EXG2_24BIT: 20,
    ESensorGroup.EXG2_16BIT: 21,
}

EXG_ADC_OFFSET = 0.0
EXG_ADC_REF_VOLT = 2.42  # Volts


def sort_sensors(sensors: List[ESensorGroup]) -> List[ESensorGroup]:
    """Sorts the sensors in the list according to the sensor order

    This function is useful to determine the order in which sensor data will appear in a data file by ordering
    the list of sensors according to their order in the file.

    Args:
        sensors: An unsorted list of sensors

    Returns:
        A list with the same sensors as content but sorted according to their appearance order in the data file

    """

    def sort_key_fn(x):
        return SensorOrder[x]

    sensors_sorted = sorted(sensors, key=sort_key_fn)
    return sensors_sorted
