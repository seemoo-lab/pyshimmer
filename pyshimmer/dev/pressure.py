# pyshimmer - API for Shimmer sensor devices
# Copyright (C) 2026  Lukas Magel

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
"""Compensation of the barometric pressure and temperature channels

The Bosch pressure sensors fitted to the Shimmer devices do not report physical
units. They report two uncompensated ADC readings which must be combined with a set
of per-device trim coefficients to obtain a pressure and a temperature. Both the
coefficients and the compensation formula are specific to the sensor model.

The formulae implemented here follow the respective Bosch datasheets and the
reference implementation of the Shimmer Java API.
"""

from __future__ import annotations

import struct
from abc import ABC, abstractmethod
from enum import Enum, auto, unique

import numpy as np


@unique
class EPressureSensor(Enum):
    """The barometric pressure sensor models fitted to the Shimmer devices"""

    # Shimmer3 with the original IMU set
    BMP180 = auto()
    # Shimmer3 with the newer IMU set, see Shimmer3Revision
    BMP280 = auto()
    # Shimmer3R
    BMP390 = auto()
    # Shimmer3R with an up-rev'd board, reports pre-compensated values
    BMP581 = auto()


class PressureCalibration(ABC):
    """Converts the uncompensated pressure channels into physical units"""

    @property
    @abstractmethod
    def sensor(self) -> EPressureSensor:
        """The sensor model for which this instance compensates"""
        pass

    @abstractmethod
    def calibrate(
        self, raw_pressure: np.ndarray, raw_temperature: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        """Compensate the raw pressure and temperature readings

        :param raw_pressure: The raw values of the pressure channel
        :param raw_temperature: The raw values of the temperature channel
        :return: A tuple of the pressure in kPa and the temperature in degrees Celsius
        """
        pass


class BMP180Calibration(PressureCalibration):

    # Coefficients are stored as signed and unsigned big-endian 16bit integers
    FMT = ">hhhHHHhhhhh"
    BLOCK_LEN = struct.calcsize(FMT)

    def __init__(self, block: bytes, oversampling: int = 0):
        """Compensation for the BMP180 of the Shimmer3

        :param block: The 22 byte calibration block stored by the device
        :param oversampling: The pressure oversampling setting of the device, which
            the firmware stores as the pressure resolution in the file header
        """
        if len(block) < self.BLOCK_LEN:
            raise ValueError(
                f"BMP180 calibration block must have length {self.BLOCK_LEN}"
            )

        (
            self.ac1,
            self.ac2,
            self.ac3,
            self.ac4,
            self.ac5,
            self.ac6,
            self.b1,
            self.b2,
            self.mb,
            self.mc,
            self.md,
        ) = struct.unpack(self.FMT, block[: self.BLOCK_LEN])

        self._oss = oversampling

    @property
    def sensor(self) -> EPressureSensor:
        return EPressureSensor.BMP180

    @property
    def oversampling(self) -> int:
        """The pressure oversampling setting of the device"""
        return self._oss

    def calibrate(
        self, raw_pressure: np.ndarray, raw_temperature: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        ut = np.asarray(raw_temperature, dtype=float)

        # The device records the full 24bit pressure register (0xF6 to 0xF8), of
        # which only the upper 16 + oss bits are significant. The datasheet formula
        # expects the reading without the unused least significant bits, see section
        # 3.5 of the BMP180 datasheet.
        up = np.asarray(raw_pressure, dtype=float) / 2 ** (8 - self._oss)

        x1 = (ut - self.ac6) * (self.ac5 / 32768)
        x2 = self.mc * 2048 / (x1 + self.md)
        b5 = x1 + x2
        t = (b5 + 8) / 16

        b6 = b5 - 4000
        x1 = (self.b2 * (b6**2 / 4096)) / 2048
        x2 = self.ac2 * b6 / 2048
        x3 = x1 + x2
        b3 = ((self.ac1 * 4 + x3) * (1 << self._oss) + 2) / 4
        x1 = self.ac3 * b6 / 8192
        x2 = (self.b1 * (b6**2 / 4096)) / 65536
        x3 = ((x1 + x2) + 2) / 4
        b4 = self.ac4 * (x3 + 32768) / 32768
        b7 = (up - b3) * (50000 >> self._oss)

        p = np.where(b7 < 2**31, (b7 * 2) / b4, (b7 / b4) * 2)
        x1 = ((p / 256.0) * (p / 256.0) * 3038) / 65536
        x2 = (-7357 * p) / 65536
        p = p + (x1 + x2 + 3791) / 16

        # The temperature is reported in units of 0.1 degrees Celsius and the
        # pressure in Pa
        return p / 1000.0, t / 10.0


class BMP280Calibration(PressureCalibration):

    # Coefficients are stored as unsigned and signed little-endian 16bit integers
    FMT = "<Hhh" + "H" + 8 * "h"
    BLOCK_LEN = struct.calcsize(FMT)

    # The Shimmer3 transmits the 20bit temperature reading of the sensor without its
    # four least significant bits, and the 20bit pressure reading shifted left by
    # four bits. Both must be restored before the compensation is applied.
    TEMPERATURE_SCALING = 16.0
    PRESSURE_SCALING = 1.0 / 16.0

    def __init__(self, block: bytes):
        """Compensation for the BMP280 of the Shimmer3

        :param block: The 24 byte calibration block stored by the device. On the
            Shimmer3 the block is split across the file header, see
            Shimmer3Revision.PRESSURE_CALIB_BLOCKS.
        """
        if len(block) < self.BLOCK_LEN:
            raise ValueError(
                f"BMP280 calibration block must have length {self.BLOCK_LEN}"
            )

        (
            self.dig_t1,
            self.dig_t2,
            self.dig_t3,
            self.dig_p1,
            self.dig_p2,
            self.dig_p3,
            self.dig_p4,
            self.dig_p5,
            self.dig_p6,
            self.dig_p7,
            self.dig_p8,
            self.dig_p9,
        ) = struct.unpack(self.FMT, block[: self.BLOCK_LEN])

    @property
    def sensor(self) -> EPressureSensor:
        return EPressureSensor.BMP280

    def calibrate(
        self, raw_pressure: np.ndarray, raw_temperature: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        adc_t = np.asarray(raw_temperature, dtype=float) * self.TEMPERATURE_SCALING
        adc_p = np.asarray(raw_pressure, dtype=float) * self.PRESSURE_SCALING

        var1 = (adc_t / 16384.0 - self.dig_t1 / 1024.0) * self.dig_t2
        var2 = (
            (adc_t / 131072.0 - self.dig_t1 / 8192.0)
            * (adc_t / 131072.0 - self.dig_t1 / 8192.0)
        ) * self.dig_t3
        t_fine = var1 + var2
        t = t_fine / 5120.0

        var1 = (t_fine / 2.0) - 64000.0
        var2 = var1 * var1 * self.dig_p6 / 32768.0
        var2 = var2 + var1 * self.dig_p5 * 2.0
        var2 = (var2 / 4.0) + (self.dig_p4 * 65536.0)
        var1 = (self.dig_p3 * var1 * var1 / 524288.0 + self.dig_p2 * var1) / 524288.0
        var1 = (1.0 + var1 / 32768.0) * self.dig_p1

        p = 1048576.0 - adc_p
        p = (p - (var2 / 4096.0)) * 6250.0 / var1
        var1 = self.dig_p9 * p * p / 2147483648.0
        var2 = p * self.dig_p8 / 32768.0
        p = p + (var1 + var2 + self.dig_p7) / 16.0

        # The compensated pressure is reported in Pa
        return p / 1000.0, t


class BMP390Calibration(PressureCalibration):

    # Coefficients are stored little-endian with mixed widths and signedness
    FMT = "<HHb" + "hhbb" + "HHbb" + "hbb"
    BLOCK_LEN = struct.calcsize(FMT)

    def __init__(self, block: bytes):
        """Compensation for the BMP390 of the Shimmer3R

        :param block: The 21 byte calibration block stored by the device
        """
        if len(block) < self.BLOCK_LEN:
            raise ValueError(
                f"BMP390 calibration block must have length {self.BLOCK_LEN}"
            )

        t1, t2, t3, p1, p2, p3, p4, p5, p6, p7, p8, p9, p10, p11 = struct.unpack(
            self.FMT, block[: self.BLOCK_LEN]
        )

        # Quantize the raw trim values as described in the BMP390 datasheet
        self.par_t1 = t1 / 2.0**-8
        self.par_t2 = t2 / 2.0**30
        self.par_t3 = t3 / 2.0**48
        self.par_p1 = (p1 - 2**14) / 2.0**20
        self.par_p2 = (p2 - 2**14) / 2.0**29
        self.par_p3 = p3 / 2.0**32
        self.par_p4 = p4 / 2.0**37
        self.par_p5 = p5 / 2.0**-3
        self.par_p6 = p6 / 2.0**6
        self.par_p7 = p7 / 2.0**8
        self.par_p8 = p8 / 2.0**15
        self.par_p9 = p9 / 2.0**48
        self.par_p10 = p10 / 2.0**48
        self.par_p11 = p11 / 2.0**65

    @property
    def sensor(self) -> EPressureSensor:
        return EPressureSensor.BMP390

    def calibrate(
        self, raw_pressure: np.ndarray, raw_temperature: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        ut = np.asarray(raw_temperature, dtype=float)
        up = np.asarray(raw_pressure, dtype=float)

        partial_1 = ut - self.par_t1
        partial_2 = partial_1 * self.par_t2
        t_lin = partial_2 + (partial_1 * partial_1) * self.par_t3

        partial_1 = self.par_p6 * t_lin
        partial_2 = self.par_p7 * t_lin**2
        partial_3 = self.par_p8 * t_lin**3
        partial_out_1 = self.par_p5 + partial_1 + partial_2 + partial_3

        partial_1 = self.par_p2 * t_lin
        partial_2 = self.par_p3 * t_lin**2
        partial_3 = self.par_p4 * t_lin**3
        partial_out_2 = up * (self.par_p1 + partial_1 + partial_2 + partial_3)

        partial_1 = up**2
        partial_2 = self.par_p9 + self.par_p10 * t_lin
        partial_3 = partial_1 * partial_2
        partial_4 = partial_3 + up**3 * self.par_p11

        p = partial_out_1 + partial_out_2 + partial_4

        # The compensated pressure is reported in Pa
        return p / 1000.0, t_lin


class BMP581Calibration(PressureCalibration):

    def __init__(self):
        """Scaling for the BMP581 of the up-rev'd Shimmer3R

        The BMP581 compensates its readings on the chip, so no trim coefficients
        exist. The raw values only need to be scaled.
        """
        pass

    @property
    def sensor(self) -> EPressureSensor:
        return EPressureSensor.BMP581

    def calibrate(
        self, raw_pressure: np.ndarray, raw_temperature: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        p = np.asarray(raw_pressure, dtype=float) / 64.0
        t = np.asarray(raw_temperature, dtype=float) / 65536.0

        return p / 1000.0, t
