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
"""Calibration of the pressure and temperature channels

Shimmer devices carry one of four Bosch barometric pressure sensors. The Shimmer3
uses the BMP180 or, on newer boards, the BMP280. The Shimmer3R uses the BMP390 or,
on newer boards, the BMP581. All four report the same two data channels,
:attr:`EChannelType.PRESSURE` and :attr:`EChannelType.TEMPERATURE`, but those
channels carry raw sensor readings that need to be converted to physical units:

- The BMP180, BMP280 and BMP390 need a set of factory calibration coefficients that
  are stored in each individual chip. The device reports them over Bluetooth and in
  the header of its SD card recordings.
- The BMP581 compensates its readings on-chip and needs no coefficients. Its raw
  values only need to be scaled.

The compensation algorithms follow the Bosch datasheets: BST-BMP180-DS000 section 3.5,
BST-BMP280-DS001 section 8.1 and the floating-point compensation of the Bosch BMP3
sensor API. They use floating-point arithmetic throughout, like the official Shimmer
host software, so that the results of this library match its output.

All functions accept a single value or a numpy array of values. They return a float
for a single value and a numpy array otherwise.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from enum import IntEnum
from typing import Protocol, Union

import numpy as np

from pyshimmer.dev.channels import EChannelType
from pyshimmer.util import fmt_hex

Numeric = Union[int, float, np.ndarray]


class EPressureSensor(IntEnum):
    """The Bosch pressure and temperature sensor fitted to a Shimmer device

    The values of the enum are the sensor identifiers that the firmware reports in
    its response to the pressure calibration command.
    """

    BMP180 = 0
    BMP280 = 1
    BMP390 = 2
    BMP581 = 3

    @property
    def coefficient_size(self) -> int:
        """The number of calibration coefficient bytes reported for the sensor

        :return: The size of the coefficient block in bytes, 0 for the BMP581
        """
        return _COEFFICIENT_SIZES[self]

    @classmethod
    def from_sensor_id(cls, sensor_id: int) -> EPressureSensor:
        """Convert a sensor identifier reported by the firmware to the enum

        :param sensor_id: The sensor identifier
        :raises ValueError: If the identifier does not belong to a known sensor
        :return: The corresponding sensor
        """
        try:
            return cls(sensor_id)
        except ValueError:
            raise ValueError(
                f"Unknown pressure sensor id {sensor_id:d}, expected one of "
                f"{[s.value for s in cls]}"
            ) from None


_COEFFICIENT_SIZES = {
    EPressureSensor.BMP180: 22,
    EPressureSensor.BMP280: 24,
    EPressureSensor.BMP390: 21,
    EPressureSensor.BMP581: 0,
}

# Byte values with which a coefficient block can be uniformly filled when it holds no
# actual coefficients: 0x00 for a block that was never written, 0xFF for erased
# memory and 0x01 for the filler that the Shimmer3 firmware returns when the legacy
# BMP180/BMP280 command does not match the fitted chip.
_BLANK_FILL_BYTES = (0x00, 0xFF, 0x01)

# Bosch compensation limits of the BMP3 sensor API
BMP390_MIN_TEMPERATURE = -40.0
BMP390_MAX_TEMPERATURE = 85.0
BMP390_MIN_PRESSURE = 30000.0
BMP390_MAX_PRESSURE = 125000.0

# Expansion board IDs of the Shimmer3, as found in the SR number of the board
EXP_BRD_SHIMMER3_IMU = 31
EXP_BRD_PROTO3_MINI = 36
EXP_BRD_PROTO3_DELUXE = 38
EXP_BRD_EXG_UNIFIED = 47
EXP_BRD_GSR_UNIFIED = 48
EXP_BRD_BR_AMP_UNIFIED = 49

# The first revision of each board that carries a BMP280 instead of a BMP180
_SHIMMER3_BMP280_MIN_REV = {
    EXP_BRD_SHIMMER3_IMU: 6,
    EXP_BRD_PROTO3_MINI: 3,
    EXP_BRD_PROTO3_DELUXE: 3,
    EXP_BRD_EXG_UNIFIED: 3,
    EXP_BRD_GSR_UNIFIED: 3,
    EXP_BRD_BR_AMP_UNIFIED: 2,
}

# A special revision that marks any expansion board attached to a newer base board
_SHIMMER3_BMP280_SPECIAL_REV = 171


def _as_float_array(v: Numeric) -> np.ndarray:
    return np.asarray(v, dtype=np.float64)


def _as_output(v: np.ndarray) -> float | np.ndarray:
    v = np.asarray(v)
    if v.ndim == 0:
        return float(v)
    return v


def sign_extend_24(value: Numeric) -> int | np.ndarray:
    """Interpret a 24-bit value as a two's complement signed integer

    Only the lower 24 bits of the value are considered, so the function is idempotent:
    a value that already is sign-extended is returned unchanged.

    :param value: The 24-bit value or an array of such values
    :return: The signed value in the range -2^23 to 2^23 - 1
    """
    bits = np.asarray(value, dtype=np.int64) & 0xFFFFFF
    extended = np.where(bits & 0x800000, bits - 0x1000000, bits)

    if extended.ndim == 0:
        return int(extended)
    return extended


def get_shimmer3_pressure_sensor(
    exp_board_id: int, exp_board_rev: int, exp_board_rev_special: int = 0
) -> EPressureSensor:
    """Determine the pressure sensor of a Shimmer3 from its expansion board

    Early Shimmer3 boards carry a BMP180, later revisions a BMP280. The chip cannot
    be told apart from the data it produces, only from the board revision.

    :param exp_board_id: The expansion board ID, the first part of the SR number
    :param exp_board_rev: The expansion board revision
    :param exp_board_rev_special: The special revision of the expansion board
    :return: The pressure sensor fitted to the device
    """
    min_rev = _SHIMMER3_BMP280_MIN_REV.get(exp_board_id, None)

    if exp_board_rev_special == _SHIMMER3_BMP280_SPECIAL_REV:
        return EPressureSensor.BMP280
    if min_rev is not None and exp_board_rev >= min_rev:
        return EPressureSensor.BMP280
    return EPressureSensor.BMP180


@dataclass(frozen=True)
class Bmp180Coefficients:
    """The calibration coefficients of the BMP180, see BST-BMP180-DS000 section 3.4"""

    ac1: int
    ac2: int
    ac3: int
    ac4: int
    ac5: int
    ac6: int
    b1: int
    b2: int
    mb: int
    mc: int
    md: int

    @classmethod
    def from_bytes(cls, coeff_bin: bytes) -> Bmp180Coefficients:
        """Parse the 22-byte coefficient block of the BMP180

        Each coefficient is a 16-bit big-endian value. AC4, AC5 and AC6 are unsigned,
        all other coefficients are signed.

        :param coeff_bin: The coefficient bytes
        :return: The parsed coefficients
        """
        return cls(*struct.unpack(">hhhHHHhhhhh", coeff_bin))


@dataclass(frozen=True)
class Bmp280Coefficients:
    """The calibration coefficients of the BMP280, see BST-BMP280-DS001 section 3.11.2"""

    dig_t1: int
    dig_t2: int
    dig_t3: int
    dig_p1: int
    dig_p2: int
    dig_p3: int
    dig_p4: int
    dig_p5: int
    dig_p6: int
    dig_p7: int
    dig_p8: int
    dig_p9: int

    @classmethod
    def from_bytes(cls, coeff_bin: bytes) -> Bmp280Coefficients:
        """Parse the 24-byte coefficient block of the BMP280

        Each coefficient is a 16-bit little-endian value. dig_T1 and dig_P1 are
        unsigned, all other coefficients are signed.

        :param coeff_bin: The coefficient bytes
        :return: The parsed coefficients
        """
        return cls(*struct.unpack("<HhhHhhhhhhhh", coeff_bin))


@dataclass(frozen=True)
class Bmp390Coefficients:
    """The quantized calibration coefficients of the BMP390

    The values are the register contents divided by their respective scaling factor,
    which is the form used by the floating-point compensation of the Bosch BMP3 sensor
    API.
    """

    par_t1: float
    par_t2: float
    par_t3: float
    par_p1: float
    par_p2: float
    par_p3: float
    par_p4: float
    par_p5: float
    par_p6: float
    par_p7: float
    par_p8: float
    par_p9: float
    par_p10: float
    par_p11: float

    @classmethod
    def from_bytes(cls, coeff_bin: bytes) -> Bmp390Coefficients:
        """Parse and quantize the 21-byte coefficient block of the BMP390

        The multi-byte coefficients are little-endian.

        :param coeff_bin: The coefficient bytes
        :return: The quantized coefficients
        """
        t1, t2, t3, p1, p2, p3, p4, p5, p6, p7, p8, p9, p10, p11 = struct.unpack(
            "<HHbhhbbHHbbhbb", coeff_bin
        )

        return cls(
            par_t1=t1 / 2.0**-8,
            par_t2=t2 / 2.0**30,
            par_t3=t3 / 2.0**48,
            par_p1=(p1 - 2**14) / 2.0**20,
            par_p2=(p2 - 2**14) / 2.0**29,
            par_p3=p3 / 2.0**32,
            par_p4=p4 / 2.0**37,
            par_p5=p5 / 2.0**-3,
            par_p6=p6 / 2.0**6,
            par_p7=p7 / 2.0**8,
            par_p8=p8 / 2.0**15,
            par_p9=p9 / 2.0**48,
            par_p10=p10 / 2.0**48,
            par_p11=p11 / 2.0**65,
        )


PressureCoefficients = Union[Bmp180Coefficients, Bmp280Coefficients, Bmp390Coefficients]


def compensate_bmp180(
    up: Numeric, ut: Numeric, coeff: Bmp180Coefficients, oversampling: int = 0
) -> tuple[float | np.ndarray, float | np.ndarray]:
    """Compensate a BMP180 reading, see BST-BMP180-DS000 section 3.5

    :param up: The uncompensated pressure UP, already right-aligned according to the
        oversampling setting
    :param ut: The uncompensated temperature UT
    :param coeff: The calibration coefficients of the chip
    :param oversampling: The oversampling setting oss of the chip, 0 to 3
    :return: The pressure in Pa and the temperature in degrees Celsius
    """
    if not 0 <= oversampling <= 3:
        raise ValueError(f"BMP180 oversampling must be 0 to 3, not {oversampling}")

    c = coeff
    up = _as_float_array(up)
    ut = _as_float_array(ut)

    with np.errstate(divide="ignore", invalid="ignore"):
        x1 = (ut - c.ac6) * c.ac5 / 32768
        x2 = c.mc * 2048 / (x1 + c.md)
        b5 = x1 + x2
        t = (b5 + 8) / 16

        b6 = b5 - 4000
        x1 = (c.b2 * (b6**2 / 4096)) / 2048
        x2 = c.ac2 * b6 / 2048
        x3 = x1 + x2
        b3 = ((c.ac1 * 4 + x3) * (1 << oversampling) + 2) / 4
        x1 = c.ac3 * b6 / 8192
        x2 = (c.b1 * (b6**2 / 4096)) / 65536
        x3 = ((x1 + x2) + 2) / 4
        b4 = c.ac4 * (x3 + 32768) / 32768
        b7 = (up - b3) * (50000 >> oversampling)
        # The datasheet distinguishes the two cases to avoid an overflow in 32-bit
        # integer arithmetic. The branch is retained for identical rounding.
        p = np.where(b7 < 0x80000000, (b7 * 2) / b4, (b7 / b4) * 2)
        x1 = ((p / 256) * (p / 256) * 3038) / 65536
        x2 = (-7357 * p) / 65536
        p = p + (x1 + x2 + 3791) / 16

    # t is in units of 0.1 degrees Celsius
    return _as_output(p), _as_output(t / 10)


def compensate_bmp280(
    adc_p: Numeric, adc_t: Numeric, coeff: Bmp280Coefficients
) -> tuple[float | np.ndarray, float | np.ndarray]:
    """Compensate a BMP280 reading, see BST-BMP280-DS001 section 8.1

    :param adc_p: The 20-bit uncompensated pressure reading
    :param adc_t: The 20-bit uncompensated temperature reading
    :param coeff: The calibration coefficients of the chip
    :return: The pressure in Pa and the temperature in degrees Celsius
    """
    c = coeff
    adc_p = _as_float_array(adc_p)
    adc_t = _as_float_array(adc_t)

    with np.errstate(divide="ignore", invalid="ignore"):
        var1 = (adc_t / 16384.0 - c.dig_t1 / 1024.0) * c.dig_t2
        var2 = (
            (adc_t / 131072.0 - c.dig_t1 / 8192.0)
            * (adc_t / 131072.0 - c.dig_t1 / 8192.0)
        ) * c.dig_t3
        t_fine = var1 + var2
        t = t_fine / 5120.0

        var1 = (t_fine / 2.0) - 64000.0
        var2 = var1 * var1 * c.dig_p6 / 32768.0
        var2 = var2 + var1 * c.dig_p5 * 2.0
        var2 = (var2 / 4.0) + (c.dig_p4 * 65536.0)
        var1 = (c.dig_p3 * var1 * var1 / 524288.0 + c.dig_p2 * var1) / 524288.0
        var1 = (1.0 + var1 / 32768.0) * c.dig_p1
        p = 1048576.0 - adc_p
        p = (p - (var2 / 4096.0)) * 6250.0 / var1
        var1 = c.dig_p9 * p * p / 2147483648.0
        var2 = p * c.dig_p8 / 32768.0
        p = p + (var1 + var2 + c.dig_p7) / 16.0

    return _as_output(p), _as_output(t)


def compensate_bmp390(
    up: Numeric, ut: Numeric, coeff: Bmp390Coefficients
) -> tuple[float | np.ndarray, float | np.ndarray]:
    """Compensate a BMP390 reading

    The function implements the floating-point compensation of the Bosch BMP3 sensor
    API, including its limits for pressure and temperature.

    :param up: The 24-bit uncompensated pressure reading
    :param ut: The 24-bit uncompensated temperature reading
    :param coeff: The quantized calibration coefficients of the chip
    :return: The pressure in Pa and the temperature in degrees Celsius
    """
    c = coeff
    up = _as_float_array(up)
    ut = _as_float_array(ut)

    partial_data1 = ut - c.par_t1
    partial_data2 = partial_data1 * c.par_t2
    t_lin = partial_data2 + (partial_data1 * partial_data1) * c.par_t3
    t_lin = np.clip(t_lin, BMP390_MIN_TEMPERATURE, BMP390_MAX_TEMPERATURE)

    partial_data1 = c.par_p6 * t_lin
    partial_data2 = c.par_p7 * t_lin**2
    partial_data3 = c.par_p8 * t_lin**3
    partial_out1 = c.par_p5 + partial_data1 + partial_data2 + partial_data3

    partial_data1 = c.par_p2 * t_lin
    partial_data2 = c.par_p3 * t_lin**2
    partial_data3 = c.par_p4 * t_lin**3
    partial_out2 = up * (c.par_p1 + partial_data1 + partial_data2 + partial_data3)

    partial_data1 = up**2
    partial_data2 = c.par_p9 + c.par_p10 * t_lin
    partial_data3 = partial_data1 * partial_data2
    partial_data4 = partial_data3 + up**3 * c.par_p11
    p = partial_out1 + partial_out2 + partial_data4
    p = np.clip(p, BMP390_MIN_PRESSURE, BMP390_MAX_PRESSURE)

    return _as_output(p), _as_output(t_lin)


def compensate_bmp581(
    up: Numeric, ut: Numeric
) -> tuple[float | np.ndarray, float | np.ndarray]:
    """Scale a BMP581 reading, see BST-BMP581-DS004

    The BMP581 compensates its readings on-chip. The pressure is an unsigned 24-bit
    value in units of 1/64 Pa, the temperature a signed 24-bit value in units of
    1/65536 degrees Celsius.

    :param up: The 24-bit pressure reading
    :param ut: The 24-bit temperature reading, interpreted as two's complement
    :return: The pressure in Pa and the temperature in degrees Celsius
    """
    p = _as_float_array(up) / 64.0
    t = _as_float_array(sign_extend_24(ut)) / 65536.0

    return _as_output(p), _as_output(t)


def prescale_raw_values(
    sensor: EPressureSensor,
    raw_pressure: Numeric,
    raw_temperature: Numeric,
    oversampling: int = 0,
) -> tuple[float | np.ndarray, float | np.ndarray]:
    """Convert the raw channel values of a Shimmer to the readings of the sensor

    The Shimmer3 does not transmit the BMP180 and BMP280 readings in the form
    that the compensation algorithms expect:

    - BMP180: the pressure channel holds the chip's left-aligned 24-bit reading,
      which needs to be shifted right by 8 - oss bits.
    - BMP280: the temperature channel omits the four least significant bits of the
      20-bit reading, and the pressure channel carries four trailing zero bits.

    The Shimmer3R transmits the BMP390 and BMP581 readings unchanged.

    :param sensor: The pressure sensor that produced the values
    :param raw_pressure: The value of the pressure channel
    :param raw_temperature: The value of the temperature channel
    :param oversampling: The oversampling setting of the chip, only used for the
        BMP180
    :return: The pressure and temperature readings of the sensor
    """
    raw_pressure = _as_float_array(raw_pressure)
    raw_temperature = _as_float_array(raw_temperature)

    if sensor == EPressureSensor.BMP180:
        return (
            _as_output(raw_pressure / 2.0 ** (8 - oversampling)),
            _as_output(raw_temperature),
        )
    elif sensor == EPressureSensor.BMP280:
        return _as_output(raw_pressure / 16.0), _as_output(raw_temperature * 16.0)

    return _as_output(raw_pressure), _as_output(raw_temperature)


class PressureChannels(Protocol):
    """Any container of channel values that can be indexed by channel type, such as a
    :class:`pyshimmer.bluetooth.bt_commands.DataPacket` or a dictionary
    """

    def __getitem__(self, item: EChannelType) -> Numeric: ...


class PressureCalibration:

    def __init__(self, sensor: EPressureSensor, coeff_bin: bytes):
        """The pressure sensor of a device together with its calibration coefficients

        :param sensor: The pressure sensor fitted to the device
        :param coeff_bin: The calibration coefficient bytes as reported by the device.
            The length must match the coefficient size of the sensor.
        :raises ValueError: If the number of coefficient bytes does not match the
            sensor
        """
        sensor = EPressureSensor(sensor)
        coeff_bin = bytes(coeff_bin)

        if len(coeff_bin) != sensor.coefficient_size:
            raise ValueError(
                f"The {sensor.name} requires {sensor.coefficient_size:d} calibration "
                f"coefficient bytes, but {len(coeff_bin):d} were provided"
            )

        self._sensor = sensor
        self._coeff_bin = coeff_bin
        self._coeff = self._parse_coefficients(sensor, coeff_bin)

    @staticmethod
    def _parse_coefficients(
        sensor: EPressureSensor, coeff_bin: bytes
    ) -> PressureCoefficients | None:
        if sensor == EPressureSensor.BMP180:
            return Bmp180Coefficients.from_bytes(coeff_bin)
        elif sensor == EPressureSensor.BMP280:
            return Bmp280Coefficients.from_bytes(coeff_bin)
        elif sensor == EPressureSensor.BMP390:
            return Bmp390Coefficients.from_bytes(coeff_bin)

        return None

    def __str__(self) -> str:
        return f"PressureCalibration({self._sensor.name}, {fmt_hex(self._coeff_bin)})"

    def __eq__(self, other: PressureCalibration) -> bool:
        if not isinstance(other, PressureCalibration):
            return False

        return self._sensor == other._sensor and self._coeff_bin == other._coeff_bin

    @property
    def sensor(self) -> EPressureSensor:
        """The pressure sensor fitted to the device"""
        return self._sensor

    @property
    def binary(self) -> bytes:
        """The calibration coefficient bytes as reported by the device"""
        return self._coeff_bin

    @property
    def coefficients(self) -> PressureCoefficients | None:
        """The parsed calibration coefficients, None for the BMP581"""
        return self._coeff

    @property
    def is_blank(self) -> bool:
        """True if the coefficient block holds no actual coefficients

        This is the case if all bytes carry the same filler value 0x00, 0xFF or 0x01.
        The latter is returned by the Shimmer3 if the legacy BMP180 or BMP280 command
        does not match the fitted chip. The BMP581 requires no coefficients and is
        never blank.
        """
        if self._sensor == EPressureSensor.BMP581:
            return False

        return any(
            self._coeff_bin == bytes([fill]) * len(self._coeff_bin)
            for fill in _BLANK_FILL_BYTES
        )

    def compensate(
        self,
        raw_pressure: Numeric,
        raw_temperature: Numeric,
        oversampling: int = 0,
    ) -> tuple[float | np.ndarray, float | np.ndarray]:
        """Convert raw pressure and temperature channel values to physical units

        The values are expected exactly as they are streamed or logged by the Shimmer.
        The necessary pre-scaling of the raw values is applied automatically.

        :param raw_pressure: The value of the :attr:`EChannelType.PRESSURE` channel,
            can be a numpy array
        :param raw_temperature: The value of the :attr:`EChannelType.TEMPERATURE`
            channel, can be a numpy array
        :param oversampling: The configured pressure oversampling setting of the
            device. Only required for the BMP180, ignored for all other sensors.
        :raises ValueError: If the coefficient block is blank
        :return: The pressure in Pa and the temperature in degrees Celsius
        """
        if self.is_blank:
            raise ValueError(
                f"The {self._sensor.name} calibration coefficients are blank "
                f"(all bytes 0x{self._coeff_bin[0]:02x}). Was the command for the "
                f"correct pressure sensor used?"
            )

        up, ut = prescale_raw_values(
            self._sensor, raw_pressure, raw_temperature, oversampling
        )

        if self._sensor == EPressureSensor.BMP180:
            return compensate_bmp180(up, ut, self._coeff, oversampling)
        elif self._sensor == EPressureSensor.BMP280:
            return compensate_bmp280(up, ut, self._coeff)
        elif self._sensor == EPressureSensor.BMP390:
            return compensate_bmp390(up, ut, self._coeff)

        return compensate_bmp581(up, ut)

    def compensate_channels(
        self, channels: PressureChannels, oversampling: int = 0
    ) -> tuple[float | np.ndarray, float | np.ndarray]:
        """Convert the pressure and temperature channels of a data packet

        :param channels: A data packet, or any other container that can be indexed by
            :class:`EChannelType`, which holds the :attr:`EChannelType.PRESSURE` and
            :attr:`EChannelType.TEMPERATURE` channels
        :param oversampling: The configured pressure oversampling setting of the
            device. Only required for the BMP180, ignored for all other sensors.
        :return: The pressure in Pa and the temperature in degrees Celsius
        """
        return self.compensate(
            channels[EChannelType.PRESSURE],
            channels[EChannelType.TEMPERATURE],
            oversampling,
        )
