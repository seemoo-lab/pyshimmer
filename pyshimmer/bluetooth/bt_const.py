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
from pyshimmer.dev.channels import EChannelType

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

"""
The Bluetooth LogAndStream API assigns a numerical index to each channel type. This dictionary maps each index to the
corresponding channel type.
"""
BtChannelsByIndex = {
    0x00: EChannelType.ACCEL_LN_X,
    0x01: EChannelType.ACCEL_LN_Y,
    0x02: EChannelType.ACCEL_LN_Z,
    0x03: EChannelType.VBATT,
    0x04: EChannelType.ACCEL_LSM303DLHC_X,
    0x05: EChannelType.ACCEL_LSM303DLHC_Y,
    0x06: EChannelType.ACCEL_LSM303DLHC_Z,
    0x07: EChannelType.MAG_LSM303DLHC_X,
    0x08: EChannelType.MAG_LSM303DLHC_Y,
    0x09: EChannelType.MAG_LSM303DLHC_Z,
    0x0A: EChannelType.GYRO_MPU9150_X,
    0x0B: EChannelType.GYRO_MPU9150_Y,
    0x0C: EChannelType.GYRO_MPU9150_Z,
    0x0D: EChannelType.EXTERNAL_ADC_7,
    0x0E: EChannelType.EXTERNAL_ADC_6,
    0x0F: EChannelType.EXTERNAL_ADC_15,
    0x10: EChannelType.INTERNAL_ADC_1,
    0x11: EChannelType.INTERNAL_ADC_12,
    0x12: EChannelType.INTERNAL_ADC_13,
    0x13: EChannelType.INTERNAL_ADC_14,
    0x14: EChannelType.ACCEL_MPU9150_X,
    0x15: EChannelType.ACCEL_MPU9150_Y,
    0x16: EChannelType.ACCEL_MPU9150_Z,
    0x17: EChannelType.MAG_MPU9150_X,
    0x18: EChannelType.MAG_MPU9150_Y,
    0x19: EChannelType.MAG_MPU9150_Z,
    0x1A: EChannelType.TEMP_BMPX80,
    0x1B: EChannelType.PRESSURE_BMPX80,
    0x1C: EChannelType.GSR_RAW,
    0x1D: EChannelType.EXG_ADS1292R_1_STATUS,
    0x1E: EChannelType.EXG_ADS1292R_1_CH1_24BIT,
    0x1F: EChannelType.EXG_ADS1292R_1_CH2_24BIT,
    0x20: EChannelType.EXG_ADS1292R_2_STATUS,
    0x21: EChannelType.EXG_ADS1292R_2_CH1_24BIT,
    0x22: EChannelType.EXG_ADS1292R_2_CH2_24BIT,
    0x23: EChannelType.EXG_ADS1292R_1_CH1_16BIT,
    0x24: EChannelType.EXG_ADS1292R_1_CH2_16BIT,
    0x25: EChannelType.EXG_ADS1292R_2_CH1_16BIT,
    0x26: EChannelType.EXG_ADS1292R_2_CH2_16BIT,
    0x27: EChannelType.STRAIN_HIGH,
    0x28: EChannelType.STRAIN_LOW,
}
