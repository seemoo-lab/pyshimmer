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

SR_OFFSET = 0x00

ENABLED_SENSORS_OFFSET = 0x03

RTC_CLOCK_DIFF_OFFSET = 0x2C

START_TS_OFFSET = 0xFB
START_TS_LEN = 0x5

TRIAL_CONFIG_OFFSET = 0x10

# The hardware version is stored as big-endian 16bit value at this offset. It is
# located in the part of the header that is common to all hardware revisions and can
# therefore be read before the layout of the remaining header is known.
HW_VERSION_OFFSET = 0x1E

# The firmware identifier and version, stored as three big-endian 16bit values
# followed by two single bytes
FW_TYPE_OFFSET = 0x22
FW_VERSION_OFFSET = 0x24

BLOCK_LEN = 0x200

TRIAL_CONFIG_SYNC = 0x04 << 8 * 0
TRIAL_CONFIG_MASTER = 0x02 << 8 * 0

EXG_REG_OFFSET = 0x38
EXG_REG_LEN = 0x0A

# Binary format of a triaxial calibration block: three offset and three gain values as
# signed big-endian 16bit integers, followed by the nine alignment matrix entries as
# signed bytes
TRIAXCAL_FMT = ">" + 6 * "h" + 9 * "b"

CONFIG_SETUP_BYTE3_OFFSET = 0x0B
# Bits 4-5 of configuration setup byte 3 hold the pressure oversampling setting
PRESSURE_OVERSAMPLING_SHIFT = 4
PRESSURE_OVERSAMPLING_MASK = 0x03
# Bits 1-3 of configuration setup byte 3 hold the range setting of the GSR circuit:
# 0 to 3 for a fixed range, 4 for auto range
GSR_RANGE_SHIFT = 1
GSR_RANGE_MASK = 0x07

EXP_BOARD_OFFSET = 0xD6
EXP_BOARD_LEN = 0x03

# The first 22 bytes of the pressure calibration coefficients. The BMP280 has two more
# coefficient bytes, which are stored separately.
PRESSURE_CALIB_OFFSET = 0xA0
PRESSURE_CALIB_LEN = 0x16
PRESSURE_CALIB_EXTRA_OFFSET = 0xDE
PRESSURE_CALIB_EXTRA_LEN = 0x02

EXG_ADC_OFFSET = 0.0
EXG_ADC_REF_VOLT = 2.42  # Volts

# Properties of the microcontroller ADC to which the analog channels are connected
ADC_OFFSET = 0.0
ADC_REF_VOLT = 3.0  # Volts
ADC_GAIN = 1.0
