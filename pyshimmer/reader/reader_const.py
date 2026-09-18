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

BLOCK_LEN = 0x200

TRIAL_CONFIG_SYNC = 0x04 << 8 * 0
TRIAL_CONFIG_MASTER = 0x02 << 8 * 0

EXG_REG_OFFSET = 0x38
EXG_REG_LEN = 0x0A

# Binary format of a triaxial calibration block: three offset and three gain values as
# signed big-endian 16bit integers, followed by the nine alignment matrix entries as
# signed bytes
TRIAXCAL_FMT = ">" + 6 * "h" + 9 * "b"

EXG_ADC_OFFSET = 0.0
EXG_ADC_REF_VOLT = 2.42  # Volts
