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
from __future__ import annotations

from collections.abc import Iterable
from enum import Enum, auto, unique
from typing import Literal

from pyshimmer.util import flatten_list, bit_is_set


class ChannelDataType:

    def __init__(self, size: int, signed: bool = True, le: bool = True):
        """Represents the binary data type and format of a Shimmer data channel

        Every channel that is recorded by a Shimmer device has a specific data type. This
        class represents the data type of a single such channel, and is capable of decoding
        binary data into the appropriate form.

        :param size: Length of the data type in Bytes
        :param signed: True if the data type is a signed integer
        :param le: True if the data type is encoded little endian, False if the
            data type is encoded big endian
        """
        self._size = size
        self._signed = signed
        self._le = le

    @property
    def little_endian(self) -> bool:
        return self._le

    @property
    def big_endian(self) -> bool:
        return not self._le

    @property
    def byte_order(self) -> Literal["little", "big"]:
        if self.big_endian:
            return "big"

        return "little"

    @property
    def signed(self) -> bool:
        return self._signed

    @property
    def size(self) -> int:
        return self._size

    def decode(self, val_bin: bytes) -> int:
        if len(val_bin) != self.size:
            raise ValueError(
                f"Binary value does not match required size: "
                f"{len(val_bin)} != {self.size}"
            )

        return int.from_bytes(val_bin, byteorder=self.byte_order, signed=self.signed)

    def encode(self, val: int) -> bytes:
        return val.to_bytes(
            length=self.size, byteorder=self.byte_order, signed=self.signed
        )


# @unique causes issues with PyCharm code indexing
# Temporarily remove before renaming items
# https://stackoverflow.com/questions/12680080/python-enums-with-attributes
@unique
class EChannelType(Enum):
    """
    Represents the content type of a single data channel recorded by a Shimmer device
    """

    # Low Noise Accelerometer X
    ACCEL_LN_X = (0x00, True)
    # Low Noise Accelerometer Y
    ACCEL_LN_Y = (0x01, True)
    # Low Noise Accelerometer Z
    ACCEL_LN_Z = (0x02, True)

    # VSenseBatt
    VBATT = (0x03, True)

    # Wide Range Accelerometer X
    # Chips: LSM303DLHC
    ACCEL_WR_X = (0x04, True)
    # Wide Range Accelerometer Y
    # Chips: LSM303DLHC
    ACCEL_WR_Y = (0x05, True)
    # Wide Range Accelerometer Z
    # Chips: LSM303DLHC
    ACCEL_WR_Z = (0x06, True)

    # Regular Magnetometer X
    # Chips: LSM303DLHC
    MAG_REG_X = (0x07, True)
    # Regular Magnetometer Y
    # Chips: LSM303DLHC
    MAG_REG_Y = (0x08, True)
    # Regular Magnetometer Z
    # Chips: LSM303DLHC
    MAG_REG_Z = (0x09, True)

    # Gyroscope X
    # Chips: MPU9150
    GYRO_X = (0x0A, True)
    # Gyroscope Y
    # Chips: MPU9150
    GYRO_Y = (0x0B, True)
    # Gyroscope Z
    # Chips: MPU9150
    GYRO_Z = (0x0C, True)

    # External ADC Channel 7 / A0
    EXTERNAL_ADC_A0 = (0x0D, True)
    # External ADC Channel 6 / A1
    EXTERNAL_ADC_A1 = (0x0E, True)
    # External ADC Channel 15 / A2
    EXTERNAL_ADC_A2 = (0x0F, True)

    # Internal ADC Channel 1 / A3
    INTERNAL_ADC_A3 = (0x10, True)
    # Internal ADC Channel 12 / A0
    INTERNAL_ADC_A0 = (0x11, True)
    # Internal ADC Channel 13 / A1
    INTERNAL_ADC_A1 = (0x12, True)
    # Internal ADC Channel 14 / A2
    INTERNAL_ADC_A2 = (0x13, True)

    # High G Accelerometer X
    # Chips: MPU9150
    ACCEL_HG_X = (0x14, True)
    # High G Accelerometer Y
    # Chips: MPU9150
    ACCEL_HG_Y = (0x15, True)
    # High G Accelerometer Z
    # Chips: MPU9150
    ACCEL_HG_Z = (0x16, True)

    # Wide-Range Magnetometer X
    # Chips: MPU9150
    MAG_WR_X = (0x17, True)
    # Wide-Range Magnetometer Y
    # Chips: MPU9150
    MAG_WR_Y = (0x18, True)
    # Wide-Range Magnetometer Z
    # Chips: MPU9150
    MAG_WR_Z = (0x19, True)

    # Temperature
    # Chips: BMPX80
    TEMPERATURE = (0x1A, True)
    # Pressure
    # Chips: BMPX80
    PRESSURE = (0x1B, True)

    # Galvanic Skin Response Raw Data
    GSR_RAW = (0x1C, True)

    # Status of ExG 1
    # Chips: ADS1292R
    EXG1_STATUS = (0x1D, True)
    # Channel 1 of ExG 1 with 24bit resolution
    # Chips: ADS1292R
    EXG1_CH1_24BIT = (0x1E, True)
    # Channel 2 of ExG 1 with 24bit resolution
    # Chips: ADS1292R
    EXG1_CH2_24BIT = (0x1F, True)
    # Status of ExG 2
    # Chips: ADS1292R
    EXG2_STATUS = (0x20, True)
    # Channel 1 of ExG 2 with 24bit resolution
    # Chips: ADS1292R
    EXG2_CH1_24BIT = (0x21, True)
    # Channel 2 of ExG 2 with 24bit resolution
    # Chips: ADS1292R
    EXG2_CH2_24BIT = (0x22, True)
    # Channel 1 of ExG 1 with 16bit resolution
    # Chips: ADS1292R
    EXG1_CH1_16BIT = (0x23, True)
    # Channel 2 of ExG 1 with 16bit resolution
    # Chips: ADS1292R
    EXG1_CH2_16BIT = (0x24, True)
    # Channel 1 of ExG 2 with 16bit resolution
    # Chips: ADS1292R
    EXG2_CH1_16BIT = (0x25, True)
    # Channel 2 of ExG 2 with 16bit resolution
    # Chips: ADS1292R
    EXG2_CH2_16BIT = (0x26, True)

    # Bridge Amp High
    STRAIN_HIGH = (0x27, True)
    # Bridge Amp Low
    STRAIN_LOW = (0x28, True)

    TIMESTAMP = (0x100, False)

    def __new__(cls, channel_id: int, is_public: bool):
        # Strips the is_public argument from the tuple and only assigns the
        # channel ID as enum value
        obj = object.__new__(cls)
        obj._value_ = channel_id
        obj._channel_id = channel_id
        obj._is_public = is_public
        return obj

    @property
    def channel_id(self) -> int:
        """Numeric representation of the channel

        The value returned here is only valid if it is a public ID. Otherwise,
        it is only used internally by the API and unknown the Shimmer.
        """
        return self._channel_id

    @property
    def is_public(self) -> bool:
        """
        Returns True if the channel type is known by the Shimmer devices.
        Some channel types are derived types and not valid for communicating
        with the Shimmer.
        """
        return self._is_public

    @classmethod
    def enum_for_id(cls, channel_id: int) -> EChannelType:
        ch_type: EChannelType = EChannelType._value2member_map_.get(channel_id, None)

        if ch_type is None or not ch_type.is_public:
            raise ValueError(
                f"Requested channel ID {channel_id:03X} "
                f"does not have a mapped EChannelType"
            )

        return ch_type


@unique
class ESensorGroup(Enum):
    """
    Represents a sensor of the Shimmer device that can be enabled/disabled via the
    Bluetooth/Consensys/... API. Since one sensor can record more than one channel,
    there is a one-to-many mapping between sensor and channels.
    """

    # Low-noise accelerometer chip KXRB5-2042
    ACCEL_LN = auto()
    # Battery sensor
    BATTERY = auto()
    # External ADC channel 7
    EXT_CH_A0 = auto()
    # External ADC channel 6
    EXT_CH_A1 = auto()
    # External ADC channel 15
    EXT_CH_A2 = auto()
    # Internal ADC channel 12
    INT_CH_A0 = auto()
    # Internal ADC channel 13, shares the ADC converter with STRAIN
    INT_CH_A1 = auto()
    # Internal ADC channel 14, shares the ADC converter with STRAIN
    INT_CH_A2 = auto()
    # Strain sensor with two channels LOW/HIGH, shares the ADC converter with A13, A14
    STRAIN = auto()
    # Internal ADC channel 1, shares its ADC converter with the GSR sensor
    INT_CH_A3 = auto()
    # GSR sensor, shares the ADC with channel A1
    GSR = auto()
    # MPU9150 Gyro Sensor
    GYRO = auto()
    # Digital accelerometer on the LSM303DLHC chip
    ACCEL_WR = auto()
    # Mag sensor on the LSM303DLHC chip
    MAG_REG = auto()
    # Accelerometer on the MPU9150 chip
    ACCEL_HG = auto()
    # Mag sensor on the MPU9150 chip
    MAG_WR = auto()
    # Temperature sensor on the MPU9150 chip, not yet available as channel in the
    # LogAndStream firmware
    TEMP = auto()
    # Pressure sensor on the BMPX80 chip
    PRESSURE = auto()
    # 24 bit channels of the first ADS1292R chip, conflicts with the corresponding
    # 16 bit channel
    EXG1_24BIT = auto()
    # 16 bit channels of the first ADS1292R chip, conflicts with the corresponding
    # 24 bit channel
    EXG1_16BIT = auto()
    # 24 bit channels of the second ADS1292R chip, conflicts with the corresponding
    # 16 bit channel
    EXG2_24BIT = auto()
    # 16 bit channels of the second ADS1292R chip, conflicts with the corresponding
    # 24 bit channel
    EXG2_16BIT = auto()


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
    ESensorGroup.TEMP: 22,
}

ENABLED_SENSORS_LEN = 0x03
SENSOR_DTYPE = ChannelDataType(size=ENABLED_SENSORS_LEN, signed=False, le=True)


def get_enabled_channels(sensors: list[ESensorGroup]) -> list[EChannelType]:
    """Determine the set of data channels for a set of enabled sensors

    There exists a one-to-many mapping between enabled sensors and their corresponding
    data channels. This function determines the set of necessary channels for a given
    set of enabled sensors.

    Args:
        sensors: A list of sensors that are enabled on a Shimmer

    Returns:
        A list of channels in the corresponding order

    """
    channels = [SensorChannelAssignment[e] for e in sensors]
    return flatten_list(channels)


def get_ch_dtypes(channels: list[EChannelType]) -> list[ChannelDataType]:
    """Return the channel data types for a set of channels

    Args:
        channels: A list of channels
    Returns:
        A list of channel data types with the same order
    """
    dtypes = [ChDataTypeAssignment[ch] for ch in channels]
    return dtypes


def sensors2bitfield(sensors: Iterable[ESensorGroup]) -> int:
    """Convert an iterable of sensors into the corresponding bitfield transmitted to
    the Shimmer

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


def bitfield2sensors(bitfield: int) -> list[ESensorGroup]:
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


def deserialize_sensors(bitfield_bin: bytes) -> list[ESensorGroup]:
    """Deserialize the list of active sensors from the three-byte input received from
    the Shimmer

    :param bitfield_bin: The input bitfield as byte string with length 3
    :return: The list of active sensors
    """
    bitfield = SENSOR_DTYPE.decode(bitfield_bin)
    return bitfield2sensors(bitfield)


def sort_sensors(sensors: Iterable[ESensorGroup]) -> list[ESensorGroup]:
    """Sorts the sensors in the list according to the sensor order

    This function is useful to determine the order in which sensor data will appear in a
    data file by ordering the list of sensors according to their order in the file.

    Args:
        sensors: An unsorted list of sensors

    Returns:
        A list with the same sensors as content but sorted according to their appearance
        order in the data file

    """

    def sort_key_fn(x):
        return SensorOrder[x]

    sensors_sorted = sorted(sensors, key=sort_key_fn)
    return sensors_sorted
