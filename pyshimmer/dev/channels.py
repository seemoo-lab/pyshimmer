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
