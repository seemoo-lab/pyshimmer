# pyshimmer - API for Shimmer sensor devices
# Copyright (C) 2023  Lukas Magel

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
import struct
from enum import Enum, auto, unique
from typing import Dict, List, Iterable

from pyshimmer.util import raise_to_next_pow, unpack, flatten_list, bit_is_set


class ChannelDataType:
    """Represents the binary data type and format of a Shimmer data channel

    Every channel that is recorded by a Shimmer device has a specific data type. This class represents the data type
    of a single such channel, and is capable of decoding binary data into the appropriate form.
    """

    def __init__(self, size: int, signed: bool = True, le: bool = True):
        self._size = size
        self._signed = signed
        self._le = le

        self._valid_size = raise_to_next_pow(self.size)
        self._needs_extend = size != self._valid_size

        self._struct_dtypes = {
            1: 'B',
            2: 'H',
            4: 'I',
            8: 'Q',
        }

    @property
    def little_endian(self) -> bool:
        return self._le

    @property
    def big_endian(self) -> bool:
        return not self._le

    @property
    def signed(self) -> bool:
        return self._signed

    @property
    def size(self) -> int:
        return self._size

    def _get_msb(self, val: bytes):
        if self.little_endian:
            return val[-1]
        else:
            return val[0]

    def _get_extension_value(self, val: bytes):
        msb = self._get_msb(val)
        is_negative = (msb >> 7) & 1 == 1

        if self.signed and is_negative:
            return b'\xFF'
        return b'\x00'

    def _extend_value(self, val: bytes) -> bytes:
        ext_value = self._get_extension_value(val)
        suffix = ext_value * (self._valid_size - self.size)

        if self.little_endian:
            return val + suffix
        else:
            return suffix + val

    def _truncate_value(self, val: bytes) -> bytes:
        if self.little_endian:
            return val[:self._size]
        else:
            return val[self._valid_size - self._size:]

    def _get_struct_format(self) -> str:
        stype = self._struct_dtypes[self._valid_size]
        if self.signed:
            stype = stype.lower()

        if self.little_endian:
            prefix = '<'
        else:
            prefix = '>'

        return prefix + stype

    def decode(self, val_bin: bytes) -> any:
        if self._needs_extend:
            val_bin = self._extend_value(val_bin)

        struct_format = self._get_struct_format()
        r_tpl = struct.unpack(struct_format, val_bin)
        return unpack(r_tpl)

    def encode(self, val: int) -> bytes:
        struct_format = self._get_struct_format()
        val_packed = struct.pack(struct_format, val)

        if self._needs_extend:
            return self._truncate_value(val_packed)

        return val_packed


@unique
class EChannelType(Enum):
    """
    Represents the content type of a single data channel recorded by a Shimmer device
    """
    ACCEL_LN_X = auto()
    ACCEL_LN_Y = auto()
    ACCEL_LN_Z = auto()
    VBATT = auto()
    ACCEL_LSM303DLHC_X = auto()
    ACCEL_LSM303DLHC_Y = auto()
    ACCEL_LSM303DLHC_Z = auto()
    MAG_LSM303DLHC_X = auto()
    MAG_LSM303DLHC_Y = auto()
    MAG_LSM303DLHC_Z = auto()
    GYRO_MPU9150_X = auto()
    GYRO_MPU9150_Y = auto()
    GYRO_MPU9150_Z = auto()
    EXTERNAL_ADC_7 = auto()
    EXTERNAL_ADC_6 = auto()
    EXTERNAL_ADC_15 = auto()
    INTERNAL_ADC_1 = auto()
    INTERNAL_ADC_12 = auto()
    INTERNAL_ADC_13 = auto()
    INTERNAL_ADC_14 = auto()
    ACCEL_MPU9150_X = auto()
    ACCEL_MPU9150_Y = auto()
    ACCEL_MPU9150_Z = auto()
    MAG_MPU9150_X = auto()
    MAG_MPU9150_Y = auto()
    MAG_MPU9150_Z = auto()
    TEMP_BMPX80 = auto()
    PRESSURE_BMPX80 = auto()
    GSR_RAW = auto()
    EXG_ADS1292R_1_STATUS = auto()
    EXG_ADS1292R_1_CH1_24BIT = auto()
    EXG_ADS1292R_1_CH2_24BIT = auto()
    EXG_ADS1292R_2_STATUS = auto()
    EXG_ADS1292R_2_CH1_24BIT = auto()
    EXG_ADS1292R_2_CH2_24BIT = auto()
    EXG_ADS1292R_1_CH1_16BIT = auto()
    EXG_ADS1292R_1_CH2_16BIT = auto()
    EXG_ADS1292R_2_CH1_16BIT = auto()
    EXG_ADS1292R_2_CH2_16BIT = auto()
    STRAIN_HIGH = auto()
    STRAIN_LOW = auto()

    TIMESTAMP = auto()


@unique
class ESensorGroup(Enum):
    """
    Represents a sensor of the Shimmer device that can be enabled/disabled via the Bluetooth/Consensys/... API.
    Since one sensor can record more than one channel, there is a one-to-many mapping between sensor and channels.
    """
    # Low-noise accelerometer chip KXRB5-2042
    ACCEL_LN = auto()
    # Battery sensor
    BATTERY = auto()
    # External ADC channel 7
    CH_A7 = auto()
    # External ADC channel 6
    CH_A6 = auto()
    # External ADC channel 15
    CH_A15 = auto()
    # Internal ADC channel 12
    CH_A12 = auto()
    # Internal ADC channel 13, shares the ADC converter with STRAIN
    CH_A13 = auto()
    # Internal ADC channel 14, shares the ADC converter with STRAIN
    CH_A14 = auto()
    # Strain sensor with two channels LOW/HIGH, shares the ADC converter with A13, A14
    STRAIN = auto()
    # Internal ADC channel 1, shares its ADC converter with the GSR sensor
    CH_A1 = auto()
    # GSR sensor, shares the ADC with channel A1
    GSR = auto()
    # MPU9150 Gyro Sensor
    GYRO = auto()
    # Digital accelerometer on the LSM303DLHC chip
    ACCEL_WR = auto()
    # Mag sensor on the LSM303DLHC chip
    MAG = auto()
    # Accelerometer on the MPU9150 chip
    ACCEL_MPU = auto()
    # Mag sensor on the MPU9150 chip
    MAG_MPU = auto()
    # Temperature sensor on the MPU9150 chip, not yet available as channel in the LogAndStream firmware
    TEMP = auto()
    # Pressure sensor on the BMPX80 chip
    PRESSURE = auto()
    # 24 bit channels of the first ADS1292R chip, conflicts with the corresponding 16 bit channel
    EXG1_24BIT = auto()
    # 16 bit channels of the first ADS1292R chip, conflicts with the corresponding 24 bit channel
    EXG1_16BIT = auto()
    # 24 bit channels of the second ADS1292R chip, conflicts with the corresponding 16 bit channel
    EXG2_24BIT = auto()
    # 16 bit channels of the second ADS1292R chip, conflicts with the corresponding 24 bit channel
    EXG2_16BIT = auto()


"""
Assigns each channel type its appropriate data type.
"""
ChDataTypeAssignment: Dict[EChannelType, ChannelDataType] = {
    EChannelType.ACCEL_LN_X: ChannelDataType(2, signed=True, le=True),
    EChannelType.ACCEL_LN_Y: ChannelDataType(2, signed=True, le=True),
    EChannelType.ACCEL_LN_Z: ChannelDataType(2, signed=True, le=True),
    EChannelType.VBATT: ChannelDataType(2, signed=True, le=True),
    EChannelType.ACCEL_LSM303DLHC_X: ChannelDataType(2, signed=True, le=True),
    EChannelType.ACCEL_LSM303DLHC_Y: ChannelDataType(2, signed=True, le=True),
    EChannelType.ACCEL_LSM303DLHC_Z: ChannelDataType(2, signed=True, le=True),
    EChannelType.MAG_LSM303DLHC_X: ChannelDataType(2, signed=True, le=True),
    EChannelType.MAG_LSM303DLHC_Y: ChannelDataType(2, signed=True, le=True),
    EChannelType.MAG_LSM303DLHC_Z: ChannelDataType(2, signed=True, le=True),
    EChannelType.GYRO_MPU9150_X: ChannelDataType(2, signed=True, le=False),
    EChannelType.GYRO_MPU9150_Y: ChannelDataType(2, signed=True, le=False),
    EChannelType.GYRO_MPU9150_Z: ChannelDataType(2, signed=True, le=False),
    EChannelType.EXTERNAL_ADC_7: ChannelDataType(2, signed=False, le=True),
    EChannelType.EXTERNAL_ADC_6: ChannelDataType(2, signed=False, le=True),
    EChannelType.EXTERNAL_ADC_15: ChannelDataType(2, signed=False, le=True),
    EChannelType.INTERNAL_ADC_1: ChannelDataType(2, signed=False, le=True),
    EChannelType.INTERNAL_ADC_12: ChannelDataType(2, signed=False, le=True),
    EChannelType.INTERNAL_ADC_13: ChannelDataType(2, signed=False, le=True),
    EChannelType.INTERNAL_ADC_14: ChannelDataType(2, signed=False, le=True),
    EChannelType.ACCEL_MPU9150_X: None,
    EChannelType.ACCEL_MPU9150_Y: None,
    EChannelType.ACCEL_MPU9150_Z: None,
    EChannelType.MAG_MPU9150_X: None,
    EChannelType.MAG_MPU9150_Y: None,
    EChannelType.MAG_MPU9150_Z: None,
    EChannelType.TEMP_BMPX80: ChannelDataType(2, signed=False, le=False),
    EChannelType.PRESSURE_BMPX80: ChannelDataType(3, signed=False, le=False),
    EChannelType.GSR_RAW: ChannelDataType(2, signed=False, le=True),
    EChannelType.EXG_ADS1292R_1_STATUS: ChannelDataType(1, signed=False, le=True),
    EChannelType.EXG_ADS1292R_1_CH1_24BIT: ChannelDataType(3, signed=True, le=False),
    EChannelType.EXG_ADS1292R_1_CH2_24BIT: ChannelDataType(3, signed=True, le=False),
    EChannelType.EXG_ADS1292R_2_STATUS: ChannelDataType(1, signed=False, le=True),
    EChannelType.EXG_ADS1292R_2_CH1_24BIT: ChannelDataType(3, signed=True, le=False),
    EChannelType.EXG_ADS1292R_2_CH2_24BIT: ChannelDataType(3, signed=True, le=False),
    EChannelType.EXG_ADS1292R_1_CH1_16BIT: ChannelDataType(2, signed=True, le=False),
    EChannelType.EXG_ADS1292R_1_CH2_16BIT: ChannelDataType(2, signed=True, le=False),
    EChannelType.EXG_ADS1292R_2_CH1_16BIT: ChannelDataType(2, signed=True, le=False),
    EChannelType.EXG_ADS1292R_2_CH2_16BIT: ChannelDataType(2, signed=True, le=False),
    EChannelType.STRAIN_HIGH: ChannelDataType(2, signed=False, le=True),
    EChannelType.STRAIN_LOW: ChannelDataType(2, signed=False, le=True),
    EChannelType.TIMESTAMP: ChannelDataType(3, signed=False, le=True)
}

"""
This dictionary contains the mapping from sensor to data channels. Since one sensor can record on multiple channels,
the mapping is one-to-many.
"""
SensorChannelAssignment: Dict[ESensorGroup, List[EChannelType]] = {
    ESensorGroup.ACCEL_LN: [EChannelType.ACCEL_LN_X, EChannelType.ACCEL_LN_Y, EChannelType.ACCEL_LN_Z],
    ESensorGroup.BATTERY: [EChannelType.VBATT],
    ESensorGroup.CH_A7: [EChannelType.EXTERNAL_ADC_7],
    ESensorGroup.CH_A6: [EChannelType.EXTERNAL_ADC_6],
    ESensorGroup.CH_A15: [EChannelType.EXTERNAL_ADC_15],
    ESensorGroup.CH_A12: [EChannelType.INTERNAL_ADC_12],
    ESensorGroup.CH_A13: [EChannelType.INTERNAL_ADC_13],
    ESensorGroup.CH_A14: [EChannelType.INTERNAL_ADC_14],
    ESensorGroup.STRAIN: [EChannelType.STRAIN_HIGH, EChannelType.STRAIN_LOW],
    ESensorGroup.CH_A1: [EChannelType.INTERNAL_ADC_1],
    ESensorGroup.GSR: [EChannelType.GSR_RAW],
    ESensorGroup.GYRO: [EChannelType.GYRO_MPU9150_X, EChannelType.GYRO_MPU9150_Y, EChannelType.GYRO_MPU9150_Z],
    ESensorGroup.ACCEL_WR: [EChannelType.ACCEL_LSM303DLHC_X, EChannelType.ACCEL_LSM303DLHC_Y,
                            EChannelType.ACCEL_LSM303DLHC_Z],
    ESensorGroup.MAG: [EChannelType.MAG_LSM303DLHC_X, EChannelType.MAG_LSM303DLHC_Y, EChannelType.MAG_LSM303DLHC_Z],
    ESensorGroup.ACCEL_MPU: [EChannelType.ACCEL_MPU9150_X, EChannelType.ACCEL_MPU9150_Y, EChannelType.ACCEL_MPU9150_Z],
    ESensorGroup.MAG_MPU: [EChannelType.MAG_MPU9150_X, EChannelType.MAG_MPU9150_Y, EChannelType.MAG_MPU9150_Z],
    ESensorGroup.PRESSURE: [EChannelType.TEMP_BMPX80, EChannelType.PRESSURE_BMPX80],
    ESensorGroup.EXG1_24BIT: [EChannelType.EXG_ADS1292R_1_STATUS, EChannelType.EXG_ADS1292R_1_CH1_24BIT,
                              EChannelType.EXG_ADS1292R_1_CH2_24BIT],
    ESensorGroup.EXG1_16BIT: [EChannelType.EXG_ADS1292R_1_STATUS, EChannelType.EXG_ADS1292R_1_CH1_16BIT,
                              EChannelType.EXG_ADS1292R_1_CH2_16BIT],
    ESensorGroup.EXG2_24BIT: [EChannelType.EXG_ADS1292R_2_STATUS, EChannelType.EXG_ADS1292R_2_CH1_24BIT,
                              EChannelType.EXG_ADS1292R_2_CH2_24BIT],
    ESensorGroup.EXG2_16BIT: [EChannelType.EXG_ADS1292R_2_STATUS, EChannelType.EXG_ADS1292R_2_CH1_16BIT,
                              EChannelType.EXG_ADS1292R_2_CH2_16BIT],

    # The MPU9150 Temp sensor is not yet available as a channel in the LogAndStream firmware
    ESensorGroup.TEMP: [],
}

"""
The sensors are enabled via a multi-byte bitfield that currently stretches a total of three bytes. This dictionary
contains the bitfield position for every sensor in this bitfield.
"""
SensorBitAssignments: Dict[ESensorGroup, int] = {
    ESensorGroup.ACCEL_LN: 0x80 << 0 * 8,
    ESensorGroup.GYRO: 0x40 << 0 * 8,
    ESensorGroup.MAG: 0x20 << 0 * 8,
    ESensorGroup.EXG1_24BIT: 0x10 << 0 * 8,
    ESensorGroup.EXG2_24BIT: 0x08 << 0 * 8,
    ESensorGroup.GSR: 0x04 << 0 * 8,
    ESensorGroup.CH_A7: 0x02 << 0 * 8,
    ESensorGroup.CH_A6: 0x01 << 0 * 8,

    ESensorGroup.STRAIN: 0x80 << 1 * 8,
    # No assignment             0x40 << 1 * 8,
    ESensorGroup.BATTERY: 0x20 << 1 * 8,
    ESensorGroup.ACCEL_WR: 0x10 << 1 * 8,
    ESensorGroup.CH_A15: 0x08 << 1 * 8,
    ESensorGroup.CH_A1: 0x04 << 1 * 8,
    ESensorGroup.CH_A12: 0x02 << 1 * 8,
    ESensorGroup.CH_A13: 0x01 << 1 * 8,

    ESensorGroup.CH_A14: 0x80 << 2 * 8,
    ESensorGroup.ACCEL_MPU: 0x40 << 2 * 8,
    ESensorGroup.MAG_MPU: 0x20 << 2 * 8,
    ESensorGroup.EXG1_16BIT: 0x10 << 2 * 8,
    ESensorGroup.EXG2_16BIT: 0x08 << 2 * 8,
    ESensorGroup.PRESSURE: 0x04 << 2 * 8,
    ESensorGroup.TEMP: 0x02 << 2 * 8,
}

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

ENABLED_SENSORS_LEN = 0x03
SENSOR_DTYPE = ChannelDataType(size=ENABLED_SENSORS_LEN, signed=False, le=True)


def get_enabled_channels(sensors: List[ESensorGroup]) -> List[EChannelType]:
    """Determine the set of data channels for a set of enabled sensors

    There exists a one-to-many mapping between enabled sensors and their corresponding data channels. This function
    determines the set of necessary channels for a given set of enabled sensors.

    Args:
        sensors: A list of sensors that are enabled on a Shimmer

    Returns:
        A list of channels in the corresponding order

    """
    channels = [SensorChannelAssignment[e] for e in sensors]
    return flatten_list(channels)


def get_ch_dtypes(channels: List[EChannelType]) -> List[ChannelDataType]:
    """Return the channel data types for a set of channels

    Args:
        channels: A list of channels
    Returns:
        A list of channel data types with the same order
    """
    dtypes = [ChDataTypeAssignment[ch] for ch in channels]
    return dtypes


def sensors2bitfield(sensors: Iterable[ESensorGroup]) -> int:
    """Convert an iterable of sensors into the corresponding bitfield transmitted to the Shimmer

    :param sensors: A list of active sensors
    :return: A bitfield that conveys the set of active sensors to the Shimmer
    """
    bitfield = 0
    for sensor in sensors:
        bit_pos = SensorBitAssignments[sensor]
        bitfield |= bit_pos

    return bitfield


def serialize_sensorlist(sensors: Iterable[ESensorGroup]) -> bytes:
    """Serialize a list of sensors to the three-byte bitfield accepted by the Shimmer

    :param sensors: The list of sensors
    :return: A byte string with length 3 that encodes the sensors
    """
    bitfield = sensors2bitfield(sensors)
    return SENSOR_DTYPE.encode(bitfield)


def bitfield2sensors(bitfield: int) -> List[ESensorGroup]:
    """Decode a bitfield returned from the Shimmer to a list of active sensors

    :param bitfield: The bitfield received from the Shimmer encoding the active sensors
    :return: The corresponding list of active sensors
    """
    enabled_sensors = []
    for sensor in ESensorGroup:
        bit_pos = SensorBitAssignments[sensor]
        if bit_is_set(bitfield, bit_pos):
            enabled_sensors += [sensor]

    return sort_sensors(enabled_sensors)


def deserialize_sensors(bitfield_bin: bytes) -> List[ESensorGroup]:
    """Deserialize the list of active sensors from the three-byte input received from the Shimmer

    :param bitfield_bin: The input bitfield as byte string with length 3
    :return: The list of active sensors
    """
    bitfield = SENSOR_DTYPE.decode(bitfield_bin)
    return bitfield2sensors(bitfield)


def sort_sensors(sensors: Iterable[ESensorGroup]) -> List[ESensorGroup]:
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
