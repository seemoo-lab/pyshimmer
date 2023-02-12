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
import re
import struct
from enum import Enum, auto, unique
from typing import Dict, List, Union, overload, Tuple, Iterable

import numpy as np

from pyshimmer.util import raise_to_next_pow, unpack, flatten_list, bit_is_set, fmt_hex

# Device clock rate in ticks per second
DEV_CLOCK_RATE: float = 32768.0

DEFAULT_BAUDRATE = 115200


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


class ExGMux(Enum):
    NORMAL = 0x00
    SHORTED = 0x01
    RLD_MEASURE = 0x02
    MVDD = 0x03
    TEMP_SENSOR = 0x04
    TEST_SIGNAL = 0x05
    RLD_DRP = 0x06
    RLD_DRM = 0x07
    RLD_DRPM = 0x08
    INPUT3 = 0x09
    RESERVED = 0x0A


class ExGRLDLead(Enum):
    RLD1P = 0x01 << 0
    RLD1N = 0x01 << 1
    RLD2P = 0x01 << 2
    RLD2N = 0x01 << 3


class ERLDRef(Enum):
    EXTERNAL = 0x00
    INTERNAL = 0x01


class ExGRegister:
    GAIN_MAP = {
        0: 6, 1: 1, 2: 2, 3: 3, 4: 4, 5: 8, 6: 12,
    }
    DATA_RATE_MAP = {
        0: 125, 1: 250, 2: 500, 3: 1000, 4: 2000, 5: 4000, 6: 8000, 7: -1
    }
    PD_BIT = 0x01 << 7
    RLD_PD_BIT = 0x01 << 5

    def __init__(self, reg_bin: bytes):
        if len(reg_bin) < 10:
            raise ValueError('Binary register content must have length 10')

        self._reg_bin = reg_bin

    def __str__(self) -> str:
        def print_ch(ch_id: int) -> str:
            return f'Channel {ch_id + 1:2d}\n' + \
                   f'\tPowerdown: {self.is_ch_powerdown(ch_id)}\n' + \
                   f'\tGain: {self.get_ch_gain(ch_id):2d}\n' + \
                   f'\tMultiplexer: {self.get_ch_mux(ch_id).name} ({self.get_ch_mux_bin(ch_id):#06b})\n'

        def fmt_rld_channels(ch_names) -> str:
            ch_names = [ch.name for ch in ch_names] if len(ch_names) > 0 else ['None']
            return ', '.join(ch_names)

        reg_bin_str = fmt_hex(self._reg_bin)
        obj_str = f'ExGRegister:\n' + \
                  f'Data Rate: {self.data_rate:4d}\n' + \
                  f'RLD Powerdown: {self.rld_powerdown}\n' + \
                  f'RLD Channels: {fmt_rld_channels(self.rld_channels)}\n' + \
                  f'RLD Reference: {self.rld_ref.name}\n' + \
                  f'Binary: {reg_bin_str}\n'
        obj_str += print_ch(0)
        obj_str += print_ch(1)
        return obj_str

    def __eq__(self, other: "ExGRegister") -> bool:
        return self._reg_bin == other._reg_bin

    @staticmethod
    def check_ch_id(ch_id: int) -> None:
        if not 0 <= ch_id <= 1:
            raise ValueError('Channel ID must be 0 or 1')

    def _get_ch_byte(self, ch_id: int) -> int:
        ch_offset = 3 + ch_id
        return self._reg_bin[ch_offset]

    def _get_rld_byte(self) -> int:
        return self._reg_bin[0x05]

    def get_ch_gain(self, ch_id: int) -> int:
        self.check_ch_id(ch_id)

        ch_byte = self._get_ch_byte(ch_id)
        gain_bin = (ch_byte & 0x70) >> 4

        return self.GAIN_MAP[gain_bin]

    def get_ch_mux_bin(self, ch_id: int) -> int:
        self.check_ch_id(ch_id)

        ch_byte = self._get_ch_byte(ch_id)
        return ch_byte & 0x0F

    def get_ch_mux(self, ch_id: int) -> ExGMux:
        return ExGMux(self.get_ch_mux_bin(ch_id))

    def is_ch_powerdown(self, ch_id: int) -> bool:
        self.check_ch_id(ch_id)

        ch_byte = self._get_ch_byte(ch_id)
        return bit_is_set(ch_byte, self.PD_BIT)

    @property
    def binary(self):
        return self._reg_bin

    @property
    def ch1_gain(self) -> int:
        return self.get_ch_gain(0)

    @property
    def ch2_gain(self) -> int:
        return self.get_ch_gain(1)

    @property
    def ch1_mux(self) -> ExGMux:
        return self.get_ch_mux(0)

    @property
    def ch2_mux(self) -> ExGMux:
        return self.get_ch_mux(1)

    @property
    def ch1_powerdown(self) -> bool:
        return self.is_ch_powerdown(0)

    @property
    def ch2_powerdown(self) -> bool:
        return self.is_ch_powerdown(1)

    @property
    def data_rate(self) -> int:
        dr_bin = self._reg_bin[0] & 0x07
        return self.DATA_RATE_MAP[dr_bin]

    @property
    def rld_powerdown(self) -> bool:
        rld_byte = self._get_rld_byte()
        return not bit_is_set(rld_byte, self.RLD_PD_BIT)

    @property
    def rld_channels(self) -> List[ExGRLDLead]:
        rld_byte = self._get_rld_byte()
        return [ch for ch in ExGRLDLead if bit_is_set(rld_byte, ch.value)]

    @property
    def rld_ref(self) -> ERLDRef:
        ref_byte = self._reg_bin[9]
        rld_ref = (ref_byte >> 1) & 0x01
        return ERLDRef(rld_ref)


def sr2dr(sr: float) -> int:
    """Calculate equivalent device-specific rate for a sample rate in Hz

    Device-specific sample rates are given in absolute clock ticks per unit of time. This function can be used to
    calculate such a rate for the Shimmer3.

    Args:
        sr(float): The sampling rate in Hz

    Returns:
        An integer which represents the equivalent device-specific sampling rate
    """
    dr_dec = DEV_CLOCK_RATE / sr
    return round(dr_dec)


def dr2sr(dr: int):
    """Calculate equivalent sampling rate for a given device-specific rate

    Device-specific sample rates are given in absolute clock ticks per unit of time. This function can be used to
    calculate a regular sampling rate in Hz from such a rate.

    Args:
        dr(int): The absolute device rate as int

    Returns:
        A floating-point number that represents the sampling rate in Hz
    """
    return DEV_CLOCK_RATE / dr


@overload
def sec2ticks(t_sec: float) -> int: ...


@overload
def sec2ticks(t_sec: np.ndarray) -> np.ndarray: ...


def sec2ticks(t_sec: Union[float, np.ndarray]) -> Union[int, np.ndarray]:
    """Calculate equivalent device clock ticks for a time in seconds

    Args:
        t_sec: A time in seconds
    Returns:
        An integer which represents the equivalent number of clock ticks
    """
    return round(t_sec * DEV_CLOCK_RATE)


@overload
def ticks2sec(t_ticks: int) -> float: ...


@overload
def ticks2sec(t_ticks: np.ndarray) -> np.ndarray: ...


def ticks2sec(t_ticks: Union[int, np.ndarray]) -> Union[float, np.ndarray]:
    """Calculate the time in seconds equivalent to a device clock ticks count

    Args:
        t_ticks: A clock tick counter for which to calculate the time in seconds
    Returns:
        A floating point time in seconds that is equivalent to the number of clock ticks
    """
    return t_ticks / DEV_CLOCK_RATE


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


class EFirmwareType(Enum):
    BtStream = auto()
    SDLog = auto()
    LogAndStream = auto()


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


ExG_ChType_Chip_Assignment: Dict[EChannelType, Tuple[int, int]] = {
    EChannelType.EXG_ADS1292R_1_CH1_24BIT: (0, 0),
    EChannelType.EXG_ADS1292R_1_CH1_16BIT: (0, 0),

    EChannelType.EXG_ADS1292R_1_CH2_24BIT: (0, 1),
    EChannelType.EXG_ADS1292R_1_CH2_16BIT: (0, 1),

    EChannelType.EXG_ADS1292R_2_CH1_24BIT: (1, 0),
    EChannelType.EXG_ADS1292R_2_CH1_16BIT: (1, 0),

    EChannelType.EXG_ADS1292R_2_CH2_24BIT: (1, 1),
    EChannelType.EXG_ADS1292R_2_CH2_16BIT: (1, 1),
}


def is_exg_ch(ch_type: EChannelType) -> bool:
    """
    Returns true if the signal that this channel type describes was recorded by a ExG chip

    Args:
        ch_type: The EChannelType of the signal

    Returns:
        True if the channel type belongs to the ExG chips, otherwise False
    """
    # This is hacky but protected by unit tests
    regex = re.compile(r'EXG_ADS1292R_\d_CH\d_\d{2}BIT')
    return regex.match(ch_type.name) is not None


def get_exg_ch(ch_type: EChannelType) -> Tuple[int, int]:
    """
    Each ExG Chip EChannelType originates from a specific ExG chip and channel. This function returns a tuple that
    specifices which chip and channel a certain signal EChannelType was recorded with.

    Args:
        ch_type: The EChannelType of the signal

    Returns:
        A tuple of ints which represents the chip id {0, 1} and the channel id {0, 1}.

    """
    return ExG_ChType_Chip_Assignment[ch_type]


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

FirmwareTypeValueAssignment = {
    0x01: EFirmwareType.BtStream,
    0x02: EFirmwareType.SDLog,
    0x03: EFirmwareType.LogAndStream,
}


def get_firmware_type(f_type: int) -> EFirmwareType:
    if f_type not in FirmwareTypeValueAssignment:
        raise ValueError(f'Unknown firmware type: 0x{f_type:x}')

    return FirmwareTypeValueAssignment[f_type]


def get_ch_dtypes(channels: List[EChannelType]) -> List[ChannelDataType]:
    """Return the channel data types for a set of channels

    Args:
        channels: A list of channels
    Returns:
        A list of channel data types with the same order
    """
    dtypes = [ChDataTypeAssignment[ch] for ch in channels]
    return dtypes


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


"""
The sensors are enabled via a multi-byte bitfield that currently stretches a total of three bytes. This dictionary
contains the bitfield position for every sensor in this bitfield.
"""
# @formatter:off
SensorBitAssignments: Dict[ESensorGroup, int] = {
    ESensorGroup.ACCEL_LN:      0x80 << 0 * 8,
    ESensorGroup.GYRO:          0x40 << 0 * 8,
    ESensorGroup.MAG:           0x20 << 0 * 8,
    ESensorGroup.EXG1_24BIT:    0x10 << 0 * 8,
    ESensorGroup.EXG2_24BIT:    0x08 << 0 * 8,
    ESensorGroup.GSR:           0x04 << 0 * 8,
    ESensorGroup.CH_A7:        0x02 << 0 * 8,
    ESensorGroup.CH_A6:        0x01 << 0 * 8,

    ESensorGroup.STRAIN:        0x80 << 1 * 8,
    # No assignment             0x40 << 1 * 8,
    ESensorGroup.BATTERY:       0x20 << 1 * 8,
    ESensorGroup.ACCEL_WR:      0x10 << 1 * 8,
    ESensorGroup.CH_A15:       0x08 << 1 * 8,
    ESensorGroup.CH_A1:        0x04 << 1 * 8,
    ESensorGroup.CH_A12:       0x02 << 1 * 8,
    ESensorGroup.CH_A13:       0x01 << 1 * 8,

    ESensorGroup.CH_A14:       0x80 << 2 * 8,
    ESensorGroup.ACCEL_MPU:     0x40 << 2 * 8,
    ESensorGroup.MAG_MPU:       0x20 << 2 * 8,
    ESensorGroup.EXG1_16BIT:    0x10 << 2 * 8,
    ESensorGroup.EXG2_16BIT:    0x08 << 2 * 8,
    ESensorGroup.PRESSURE:      0x04 << 2 * 8,
    ESensorGroup.TEMP:          0x02 << 2 * 8,
}
# @formatter:on


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


def bitfield2sensors(bitfield: int) -> List[ESensorGroup]:
    enabled_sensors = []
    for sensor in ESensorGroup:
        bit_pos = SensorBitAssignments[sensor]
        if bit_is_set(bitfield, bit_pos):
            enabled_sensors += [sensor]

    return sort_sensors(enabled_sensors)


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
