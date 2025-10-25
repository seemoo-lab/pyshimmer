import numpy as np
from typing import Iterable

from ..channels import EChannelType, ChannelDataType, ESensorGroup
from ..revision import HardwareRevision
from pyshimmer.util import flatten_list

"""
Assigns each channel type its appropriate data type.
"""
ChDataTypeAssignment: dict[EChannelType, ChannelDataType] = {
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
    EChannelType.GYRO_X: ChannelDataType(2, signed=True, le=False),
    EChannelType.GYRO_Y: ChannelDataType(2, signed=True, le=False),
    EChannelType.GYRO_Z: ChannelDataType(2, signed=True, le=False),
    EChannelType.EXTERNAL_ADC_A0: ChannelDataType(2, signed=False, le=True),
    EChannelType.EXTERNAL_ADC_A1: ChannelDataType(2, signed=False, le=True),
    EChannelType.EXTERNAL_ADC_A2: ChannelDataType(2, signed=False, le=True),
    EChannelType.INTERNAL_ADC_A3: ChannelDataType(2, signed=False, le=True),
    EChannelType.INTERNAL_ADC_A0: ChannelDataType(2, signed=False, le=True),
    EChannelType.INTERNAL_ADC_A1: ChannelDataType(2, signed=False, le=True),
    EChannelType.INTERNAL_ADC_A2: ChannelDataType(2, signed=False, le=True),
    EChannelType.ACCEL_HG_X: None,
    EChannelType.ACCEL_HG_Y: None,
    EChannelType.ACCEL_HG_Z: None,
    EChannelType.MAG_WR_X: None,
    EChannelType.MAG_WR_Y: None,
    EChannelType.MAG_WR_Z: None,
    EChannelType.TEMPERATURE: ChannelDataType(2, signed=False, le=False),
    EChannelType.PRESSURE: ChannelDataType(3, signed=False, le=False),
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

"""
This dictionary contains the mapping from sensor to data channels. Since one sensor can
record on multiple channels, the mapping is one-to-many.
"""
SensorChannelAssignment: dict[ESensorGroup, list[EChannelType]] = {
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

"""
The sensors are enabled via a multi-byte bitfield that currently stretches a total of
three bytes. This dictionary contains the bitfield position for every sensor in this
bitfield.
"""
SensorBitAssignments: dict[ESensorGroup, int] = {
    ESensorGroup.ACCEL_LN: 0x80 << 0 * 8,
    ESensorGroup.GYRO: 0x40 << 0 * 8,
    ESensorGroup.MAG_REG: 0x20 << 0 * 8,
    ESensorGroup.EXG1_24BIT: 0x10 << 0 * 8,
    ESensorGroup.EXG2_24BIT: 0x08 << 0 * 8,
    ESensorGroup.GSR: 0x04 << 0 * 8,
    ESensorGroup.EXT_CH_A0: 0x02 << 0 * 8,
    ESensorGroup.EXT_CH_A1: 0x01 << 0 * 8,
    ESensorGroup.STRAIN: 0x80 << 1 * 8,
    # No assignment             0x40 << 1 * 8,
    ESensorGroup.BATTERY: 0x20 << 1 * 8,
    ESensorGroup.ACCEL_WR: 0x10 << 1 * 8,
    ESensorGroup.EXT_CH_A2: 0x08 << 1 * 8,
    ESensorGroup.INT_CH_A3: 0x04 << 1 * 8,
    ESensorGroup.INT_CH_A0: 0x02 << 1 * 8,
    ESensorGroup.INT_CH_A1: 0x01 << 1 * 8,
    ESensorGroup.INT_CH_A2: 0x80 << 2 * 8,
    ESensorGroup.ACCEL_HG: 0x40 << 2 * 8,
    ESensorGroup.MAG_WR: 0x20 << 2 * 8,
    ESensorGroup.EXG1_16BIT: 0x10 << 2 * 8,
    ESensorGroup.EXG2_16BIT: 0x08 << 2 * 8,
    ESensorGroup.PRESSURE: 0x04 << 2 * 8,
    ESensorGroup.TEMP: 0x02 << 2 * 8,
}

SensorOrder: dict[ESensorGroup, int] = {
    ESensorGroup.ACCEL_LN: 1,
    ESensorGroup.BATTERY: 2,
    ESensorGroup.EXT_CH_A0: 3,
    ESensorGroup.EXT_CH_A1: 4,
    ESensorGroup.EXT_CH_A2: 5,
    ESensorGroup.INT_CH_A0: 6,
    ESensorGroup.INT_CH_A1: 7,
    ESensorGroup.INT_CH_A2: 8,
    ESensorGroup.STRAIN: 9,
    ESensorGroup.INT_CH_A3: 10,
    ESensorGroup.GSR: 11,
    ESensorGroup.GYRO: 12,
    ESensorGroup.ACCEL_WR: 13,
    ESensorGroup.MAG_REG: 14,
    ESensorGroup.ACCEL_HG: 15,
    ESensorGroup.MAG_WR: 16,
    ESensorGroup.PRESSURE: 17,
    ESensorGroup.EXG1_24BIT: 18,
    ESensorGroup.EXG1_16BIT: 19,
    ESensorGroup.EXG2_24BIT: 20,
    ESensorGroup.EXG2_16BIT: 21,
}

ENABLED_SENSORS_LEN = 0x03
SENSOR_DTYPE = ChannelDataType(size=ENABLED_SENSORS_LEN, signed=False, le=True)


class Shimmer3Revision(HardwareRevision):

    # Device clock rate in ticks per second
    DEV_CLOCK_RATE: float = 32768.0

    def sr2dr(self, sr: float) -> int:
        dr_dec = self.DEV_CLOCK_RATE / sr
        return round(dr_dec)

    def dr2sr(self, dr: int) -> float:
        return self.DEV_CLOCK_RATE / dr

    def sec2ticks(self, t_sec: float | np.ndarray) -> int | np.ndarray:
        return round(t_sec * self.DEV_CLOCK_RATE)

    def ticks2sec(self, t_ticks: int | np.ndarray) -> float | np.ndarray:
        return t_ticks / self.DEV_CLOCK_RATE

    def get_channel_dtypes(
        self, channels: Iterable[EChannelType]
    ) -> list[ChannelDataType]:
        dtypes = [ChDataTypeAssignment[ch] for ch in channels]
        return dtypes

    def get_enabled_channels(
        self, sensors: Iterable[ESensorGroup]
    ) -> list[EChannelType]:
        channels = [SensorChannelAssignment[e] for e in sensors]
        return flatten_list(channels)

    def sensors2bitfield(self, sensors: Iterable[ESensorGroup]) -> int:
        bitfield = 0
        for sensor in sensors:
            bit_pos = SensorBitAssignments[sensor]
            bitfield |= bit_pos

        return bitfield

    def serialize_sensorlist(self, sensors: Iterable[ESensorGroup]) -> bytes:
        pass

    def bitfield2sensors(self, bitfield: int) -> list[ESensorGroup]:
        pass

    def deserialize_sensorlist(self, bitfield_bin: bytes) -> list[ESensorGroup]:
        pass

    def sort_sensors(self, sensors: Iterable[ESensorGroup]) -> list[ESensorGroup]:
        pass
