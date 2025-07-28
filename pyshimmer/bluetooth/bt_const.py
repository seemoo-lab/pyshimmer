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

ACK_COMMAND_PROCESSED = 0xFF
INSTREAM_CMD_RESPONSE = 0x8A
DATA_PACKET = 0x00

INQUIRY_COMMAND = 0x01
INQUIRY_RESPONSE = 0x02

GET_SAMPLING_RATE_COMMAND = 0x03
SAMPLING_RATE_RESPONSE = 0x04

SET_SAMPLING_RATE_COMMAND = 0x05

GET_BATTERY_COMMAND = 0x95
BATTERY_RESPONSE = 0x94
FULL_BATTERY_RESPONSE = bytes((INSTREAM_CMD_RESPONSE, BATTERY_RESPONSE))

START_STREAMING_COMMAND = 0x07
# No response for command

SET_SENSORS_COMMAND = 0x08
# No response for command

STOP_STREAMING_COMMAND = 0x20
# No response for command

GET_SHIMMER_VERSION_COMMAND = 0x3F
SHIMMER_VERSION_RESPONSE = 0x25

GET_CONFIGTIME_COMMAND = 0x87
CONFIGTIME_RESPONSE = 0x86

SET_CONFIGTIME_COMMAND = 0x85
# No response for set command

GET_RWC_COMMAND = 0x91
RWC_RESPONSE = 0x90

SET_RWC_COMMAND = 0x8F
# No response for set command

GET_STATUS_COMMAND = 0x72
STATUS_RESPONSE = 0x71
FULL_STATUS_RESPONSE = bytes((INSTREAM_CMD_RESPONSE, STATUS_RESPONSE))

GET_FW_VERSION_COMMAND = 0x2E
FW_VERSION_RESPONSE = 0x2F

GET_EXG_REGS_COMMAND = 0x63
EXG_REGS_RESPONSE = 0x62

SET_EXG_REGS_COMMAND = 0x61
# No response for set command

GET_EXPID_COMMAND = 0x7E
EXPID_RESPONSE = 0x7D

SET_EXPID_COMMAND = 0x7C
# No response for set command

GET_SHIMMERNAME_COMMAND = 0x7B
SHIMMERNAME_RESPONSE = 0x7A

SET_SHIMMERNAME_COMMAND = 0x79
# No response for set command

DUMMY_COMMAND = 0x96

START_LOGGING_COMMAND = 0x92
STOP_LOGGING_COMMAND = 0x93

ENABLE_STATUS_ACK_COMMAND = 0xA3

GET_ALL_CALIBRATION_COMMAND = 0x2C
ALL_CALIBRATION_RESPONSE = 0x2D
