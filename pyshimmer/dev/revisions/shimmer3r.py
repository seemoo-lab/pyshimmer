# pyshimmer - API for Shimmer sensor devices
# Copyright (C) 2025  Lukas Magel

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

from .hw_version import HardwareVersion
from .revision import BaseRevision
from ..calibration import TriaxCalibSpec
from ..channels import (
    EChannelType,
    ChannelDataType,
    ESensorGroup,
    PackedChannelDataType,
)


class Shimmer3RRevision(BaseRevision):

    # Device clock rate in ticks per second
    DEV_CLOCK_RATE: float = 32768.0
    ENABLED_SENSORS_LEN = 0x03
    SENSOR_DTYPE = ChannelDataType(size=ENABLED_SENSORS_LEN, signed=False, le=True)

    # The Shimmer3R uses a larger configuration header than the Shimmer3
    SD_HEADER_LEN = 0x180

    # The header records the number of channels, followed by one channel id per
    # channel. This list determines the set and order of the recorded channels.
    SD_CHANNEL_LIST_OFFSET = 0x13A

    TRIAXCAL_SPECS: dict[ESensorGroup, TriaxCalibSpec] = {
        ESensorGroup.ACCEL_LN: TriaxCalibSpec(offset=0x8B, alignment_scaling=100.0),
        ESensorGroup.ACCEL_WR: TriaxCalibSpec(offset=0x4C, alignment_scaling=100.0),
        ESensorGroup.GYRO: TriaxCalibSpec(
            offset=0x61, gain_scaling=100.0, alignment_scaling=100.0
        ),
        ESensorGroup.MAG_REG: TriaxCalibSpec(offset=0x76, alignment_scaling=100.0),
        ESensorGroup.ACCEL_HG: TriaxCalibSpec(offset=0x100, alignment_scaling=100.0),
        ESensorGroup.MAG_WR: TriaxCalibSpec(offset=0x11D, alignment_scaling=100.0),
    }

    CH_DTYPE_ASSIGNMENT: dict[EChannelType, ChannelDataType] = {
        EChannelType.ACCEL_LN_X: ChannelDataType(2, signed=True, le=True),
        EChannelType.ACCEL_LN_Y: ChannelDataType(2, signed=True, le=True),
        EChannelType.ACCEL_LN_Z: ChannelDataType(2, signed=True, le=True),
        EChannelType.VBATT: ChannelDataType(2, signed=True, le=True),
        EChannelType.ACCEL_WR_X: ChannelDataType(2, signed=True, le=True),
        EChannelType.ACCEL_WR_Y: ChannelDataType(2, signed=True, le=True),
        EChannelType.ACCEL_WR_Z: ChannelDataType(2, signed=True, le=True),
        EChannelType.MAG_REG_X: ChannelDataType(2, signed=True, le=True),
        EChannelType.MAG_REG_Y: ChannelDataType(2, signed=True, le=True),
        EChannelType.MAG_REG_Z: ChannelDataType(2, signed=True, le=True),
        EChannelType.GYRO_X: ChannelDataType(2, signed=True, le=True),
        EChannelType.GYRO_Y: ChannelDataType(2, signed=True, le=True),
        EChannelType.GYRO_Z: ChannelDataType(2, signed=True, le=True),
        EChannelType.EXTERNAL_ADC_A0: ChannelDataType(2, signed=False, le=True),
        EChannelType.EXTERNAL_ADC_A1: ChannelDataType(2, signed=False, le=True),
        EChannelType.EXTERNAL_ADC_A2: ChannelDataType(2, signed=False, le=True),
        EChannelType.INTERNAL_ADC_A3: ChannelDataType(2, signed=False, le=True),
        EChannelType.INTERNAL_ADC_A0: ChannelDataType(2, signed=False, le=True),
        EChannelType.INTERNAL_ADC_A1: ChannelDataType(2, signed=False, le=True),
        EChannelType.INTERNAL_ADC_A2: ChannelDataType(2, signed=False, le=True),
        # The high-g accelerometer transmits 12 bit values which are left-aligned
        # within a big-endian 16 bit word
        EChannelType.ACCEL_HG_X: PackedChannelDataType(
            2, bits=12, signed=True, le=False
        ),
        EChannelType.ACCEL_HG_Y: PackedChannelDataType(
            2, bits=12, signed=True, le=False
        ),
        EChannelType.ACCEL_HG_Z: PackedChannelDataType(
            2, bits=12, signed=True, le=False
        ),
        EChannelType.MAG_WR_X: ChannelDataType(2, signed=True, le=True),
        EChannelType.MAG_WR_Y: ChannelDataType(2, signed=True, le=True),
        EChannelType.MAG_WR_Z: ChannelDataType(2, signed=True, le=True),
        EChannelType.TEMPERATURE: ChannelDataType(3, signed=False, le=True),
        EChannelType.PRESSURE: ChannelDataType(3, signed=False, le=True),
        EChannelType.GSR_RAW: ChannelDataType(2, signed=False, le=True),
        EChannelType.EXG1_STATUS: ChannelDataType(1, signed=False, le=True),
        EChannelType.EXG1_CH1_24BIT: ChannelDataType(3, signed=True, le=False),
        EChannelType.EXG1_CH2_24BIT: ChannelDataType(3, signed=True, le=False),
        EChannelType.EXG2_STATUS: ChannelDataType(1, signed=False, le=True),
        EChannelType.EXG2_CH1_24BIT: ChannelDataType(3, signed=True, le=False),
        EChannelType.EXG2_CH2_24BIT: ChannelDataType(3, signed=True, le=False),
        EChannelType.EXG1_CH1_16BIT: ChannelDataType(2, signed=True, le=False),
        EChannelType.EXG1_CH2_16BIT: ChannelDataType(2, signed=True, le=False),
        EChannelType.EXG2_CH1_16BIT: ChannelDataType(2, signed=True, le=False),
        EChannelType.EXG2_CH2_16BIT: ChannelDataType(2, signed=True, le=False),
        EChannelType.STRAIN_HIGH: ChannelDataType(2, signed=False, le=True),
        EChannelType.STRAIN_LOW: ChannelDataType(2, signed=False, le=True),
        EChannelType.TIMESTAMP: ChannelDataType(3, signed=False, le=True),
    }

    SENSOR_CHANNEL_ASSIGNMENT: dict[ESensorGroup, list[EChannelType]] = {
        ESensorGroup.ACCEL_LN: [
            EChannelType.ACCEL_LN_X,
            EChannelType.ACCEL_LN_Y,
            EChannelType.ACCEL_LN_Z,
        ],
        ESensorGroup.BATTERY: [EChannelType.VBATT],
        ESensorGroup.EXT_CH_A0: [EChannelType.EXTERNAL_ADC_A0],
        ESensorGroup.EXT_CH_A1: [EChannelType.EXTERNAL_ADC_A1],
        ESensorGroup.EXT_CH_A2: [EChannelType.EXTERNAL_ADC_A2],
        ESensorGroup.INT_CH_A0: [EChannelType.INTERNAL_ADC_A0],
        ESensorGroup.INT_CH_A1: [EChannelType.INTERNAL_ADC_A1],
        ESensorGroup.INT_CH_A2: [EChannelType.INTERNAL_ADC_A2],
        ESensorGroup.STRAIN: [EChannelType.STRAIN_HIGH, EChannelType.STRAIN_LOW],
        ESensorGroup.INT_CH_A3: [EChannelType.INTERNAL_ADC_A3],
        ESensorGroup.GSR: [EChannelType.GSR_RAW],
        ESensorGroup.GYRO: [
            EChannelType.GYRO_X,
            EChannelType.GYRO_Y,
            EChannelType.GYRO_Z,
        ],
        ESensorGroup.ACCEL_WR: [
            EChannelType.ACCEL_WR_X,
            EChannelType.ACCEL_WR_Y,
            EChannelType.ACCEL_WR_Z,
        ],
        ESensorGroup.MAG_REG: [
            EChannelType.MAG_REG_X,
            EChannelType.MAG_REG_Y,
            EChannelType.MAG_REG_Z,
        ],
        ESensorGroup.ACCEL_HG: [
            EChannelType.ACCEL_HG_X,
            EChannelType.ACCEL_HG_Y,
            EChannelType.ACCEL_HG_Z,
        ],
        ESensorGroup.MAG_WR: [
            EChannelType.MAG_WR_X,
            EChannelType.MAG_WR_Y,
            EChannelType.MAG_WR_Z,
        ],
        ESensorGroup.PRESSURE: [EChannelType.TEMPERATURE, EChannelType.PRESSURE],
        ESensorGroup.EXG1_24BIT: [
            EChannelType.EXG1_STATUS,
            EChannelType.EXG1_CH1_24BIT,
            EChannelType.EXG1_CH2_24BIT,
        ],
        ESensorGroup.EXG1_16BIT: [
            EChannelType.EXG1_STATUS,
            EChannelType.EXG1_CH1_16BIT,
            EChannelType.EXG1_CH2_16BIT,
        ],
        ESensorGroup.EXG2_24BIT: [
            EChannelType.EXG2_STATUS,
            EChannelType.EXG2_CH1_24BIT,
            EChannelType.EXG2_CH2_24BIT,
        ],
        ESensorGroup.EXG2_16BIT: [
            EChannelType.EXG2_STATUS,
            EChannelType.EXG2_CH1_16BIT,
            EChannelType.EXG2_CH2_16BIT,
        ],
        # The MPU9150 Temp sensor is not yet available as a channel in the LogAndStream
        # firmware
        ESensorGroup.TEMP: [],
    }

    SENSOR_BIT_ASSIGNMENT: dict[ESensorGroup, int] = {
        ESensorGroup.EXT_CH_A1: 0,
        ESensorGroup.EXT_CH_A0: 1,
        ESensorGroup.GSR: 2,
        ESensorGroup.EXG2_24BIT: 3,
        ESensorGroup.EXG1_24BIT: 4,
        ESensorGroup.MAG_REG: 5,
        ESensorGroup.GYRO: 6,
        ESensorGroup.ACCEL_LN: 7,
        ESensorGroup.INT_CH_A1: 8,
        ESensorGroup.INT_CH_A0: 9,
        ESensorGroup.INT_CH_A3: 10,
        ESensorGroup.EXT_CH_A2: 11,
        ESensorGroup.ACCEL_WR: 12,
        ESensorGroup.BATTERY: 13,
        # No assignment 14
        ESensorGroup.STRAIN: 15,
        # No assignment 16
        ESensorGroup.TEMP: 17,
        ESensorGroup.PRESSURE: 18,
        ESensorGroup.EXG2_16BIT: 19,
        ESensorGroup.EXG1_16BIT: 20,
        ESensorGroup.MAG_WR: 21,
        ESensorGroup.ACCEL_HG: 22,
        ESensorGroup.INT_CH_A2: 23,
    }

    # The order in which the channels of a sensor appear in a binary data file is read
    # from the channel list in the file header, see SD_CHANNEL_LIST_OFFSET. This
    # ordering is therefore not used to lay out the data of a file. It only determines
    # the order in which the enabled sensors are reported and follows the channel ids
    # that the firmware assigns to the sensors.
    SENSOR_ORDER: dict[ESensorGroup, int] = {
        ESensorGroup.ACCEL_LN: 1,
        ESensorGroup.BATTERY: 2,
        ESensorGroup.ACCEL_WR: 3,
        ESensorGroup.MAG_REG: 4,
        ESensorGroup.GYRO: 5,
        ESensorGroup.EXT_CH_A0: 6,
        ESensorGroup.EXT_CH_A1: 7,
        ESensorGroup.EXT_CH_A2: 8,
        ESensorGroup.INT_CH_A3: 9,
        ESensorGroup.INT_CH_A0: 10,
        ESensorGroup.INT_CH_A1: 11,
        ESensorGroup.INT_CH_A2: 12,
        ESensorGroup.ACCEL_HG: 13,
        ESensorGroup.MAG_WR: 14,
        ESensorGroup.PRESSURE: 15,
        ESensorGroup.GSR: 16,
        ESensorGroup.EXG1_24BIT: 17,
        ESensorGroup.EXG1_16BIT: 18,
        ESensorGroup.EXG2_24BIT: 19,
        ESensorGroup.EXG2_16BIT: 20,
        ESensorGroup.STRAIN: 21,
        ESensorGroup.TEMP: 22,
    }

    def __init__(self):
        super().__init__(
            HardwareVersion.SHIMMER3R,
            self.DEV_CLOCK_RATE,
            self.SENSOR_DTYPE,
            self.CH_DTYPE_ASSIGNMENT,
            self.SENSOR_CHANNEL_ASSIGNMENT,
            self.SENSOR_BIT_ASSIGNMENT,
            self.SENSOR_ORDER,
            self.SD_HEADER_LEN,
            self.TRIAXCAL_SPECS,
            sd_channel_list_offset=self.SD_CHANNEL_LIST_OFFSET,
            # Synchronized Shimmer3R recordings are not supported yet
            is_sd_sync_supported=False,
        )
