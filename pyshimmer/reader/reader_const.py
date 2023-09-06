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

from pyshimmer.dev.channels import ESensorGroup

SR_OFFSET = 0x00

ENABLED_SENSORS_OFFSET = 0x03

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

EXG_ADC_OFFSET = 0.0
EXG_ADC_REF_VOLT = 2.42  # Volts
