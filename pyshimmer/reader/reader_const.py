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
from __future__ import annotations

from pyshimmer.dev.channels import ESensorGroup
from pyshimmer.dev.fw_version import FirmwareVersion

SR_OFFSET = 0x00

ENABLED_SENSORS_OFFSET = 0x03

RTC_CLOCK_DIFF_OFFSET = 0x2C

START_TS_OFFSET = 0xFB
START_TS_LEN = 0x5

TRIAL_CONFIG_OFFSET = 0x10

# The hardware version and the firmware type are 16-bit big-endian values. The firmware
# type is followed by the firmware version: a 16-bit big-endian major version, the
# minor version and the patch level.
HW_VERSION_OFFSET = 0x1E
FW_TYPE_OFFSET = 0x22

DATA_LOG_OFFSET = 0x100
BLOCK_LEN = 0x200

TRIAL_CONFIG_SYNC = 0x04 << 8 * 0
TRIAL_CONFIG_MASTER = 0x02 << 8 * 0

EXG_REG_OFFSET = 0x38
EXG_REG_LEN = 0x0A

CONFIG_SETUP_BYTE3_OFFSET = 0x0B
# Bits 4-5 of configuration setup byte 3 hold the pressure oversampling setting
PRESSURE_OVERSAMPLING_SHIFT = 4
PRESSURE_OVERSAMPLING_MASK = 0x03

EXP_BOARD_OFFSET = 0xD6
EXP_BOARD_LEN = 0x03

# The first 22 bytes of the pressure calibration coefficients. The BMP280 has two more
# coefficient bytes, which are stored separately.
PRESSURE_CALIB_OFFSET = 0xA0
PRESSURE_CALIB_LEN = 0x16
PRESSURE_CALIB_EXTRA_OFFSET = 0xDE
PRESSURE_CALIB_EXTRA_LEN = 0x02

# Newer LogAndStream firmware records the detected pressure sensor in the header. Bits
# 0-6 hold the sensor ID of EPressureSensor, bit 7 marks an ID that the firmware
# inferred from the SR number of the board because the chip ID was inconclusive.
# Older firmware leaves the byte at 0xFF.
PRESSURE_SENSOR_ID_OFFSET = 0xE0
PRESSURE_SENSOR_ID_MASK = 0x7F
PRESSURE_SENSOR_ID_INFERRED = 0x80
PRESSURE_SENSOR_ID_NONE = 0xFE
PRESSURE_SENSOR_ID_UNSET = 0xFF
# The first Shimmer3 LogAndStream firmware that records the pressure sensor
PRESSURE_SENSOR_ID_MIN_FW_SHIMMER3 = FirmwareVersion(1, 1, 6)

# The file offsets at which the calibration parameters of the respective sensor can be
# found
TRIAXCAL_FILE_OFFSET = {
    ESensorGroup.ACCEL_LN: 0x8B,
    ESensorGroup.ACCEL_WR: 0x4C,
    ESensorGroup.GYRO: 0x61,
    ESensorGroup.MAG_REG: 0x76,
}

# Scaling value by which the calibration offset will be scaled upon deserialization
TRIAXCAL_OFFSET_SCALING = {
    ESensorGroup.ACCEL_LN: 1.0,
    ESensorGroup.ACCEL_WR: 1.0,
    ESensorGroup.GYRO: 1.0,
    ESensorGroup.MAG_REG: 1.0,
}

# Scaling value by which the calibration gain will be scaled upon deserialization
TRIAXCAL_GAIN_SCALING = {
    ESensorGroup.ACCEL_LN: 1.0,
    ESensorGroup.ACCEL_WR: 1.0,
    ESensorGroup.GYRO: 1.0 / 100.0,
    ESensorGroup.MAG_REG: 1.0,
}

# Scaling value by which the calibration alignment matrix will be scaled upon
# deserialization
TRIAXCAL_ALIGNMENT_SCALING = {
    ESensorGroup.ACCEL_LN: 1.0 / 100.0,
    ESensorGroup.ACCEL_WR: 1.0 / 100.0,
    ESensorGroup.GYRO: 1.0 / 100.0,
    ESensorGroup.MAG_REG: 1.0 / 100.0,
}

TRIAXCAL_SENSORS = list(TRIAXCAL_FILE_OFFSET.keys())

EXG_ADC_OFFSET = 0.0
EXG_ADC_REF_VOLT = 2.42  # Volts
