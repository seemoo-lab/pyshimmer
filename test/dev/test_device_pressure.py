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
from __future__ import annotations

import numpy as np
import pytest

from pyshimmer.dev.pressure import (
    BMP180Calibration,
    BMP280Calibration,
    BMP390Calibration,
    BMP581Calibration,
    EPressureSensor,
)


class TestBMP280Calibration:

    # Calibration block of a Shimmer3 with a BMP280, as stored in the header of a
    # binary data file. The device stores the block in two parts, the first 22 bytes
    # at offset 0xA0 and the remaining two bytes at offset 0xDE.
    BLOCK = bytes.fromhex("7a6a0d6632007f9016d7d00bbc1b2afff9ff8c3cf8c67017")

    @pytest.fixture
    def calib(self) -> BMP280Calibration:
        return BMP280Calibration(self.BLOCK)

    def test_sensor(self, calib: BMP280Calibration):
        assert calib.sensor == EPressureSensor.BMP280

    def test_short_block(self):
        with pytest.raises(ValueError):
            BMP280Calibration(self.BLOCK[:-1])

    def test_coefficients(self, calib: BMP280Calibration):
        assert calib.dig_t1 == 27258
        assert calib.dig_t2 == 26125
        assert calib.dig_t3 == 50
        assert calib.dig_p1 == 36991
        assert calib.dig_p2 == -10474
        assert calib.dig_p3 == 3024
        assert calib.dig_p4 == 7100
        assert calib.dig_p5 == -214
        assert calib.dig_p6 == -7
        assert calib.dig_p7 == 15500
        assert calib.dig_p8 == -14600
        assert calib.dig_p9 == 6000

    def test_calibrate(self, calib: BMP280Calibration):
        # Raw readings of a steady-state sample of the same recording, along with the
        # values that the Shimmer reference tooling reports for them
        raw_pressure = np.array([5540976])
        raw_temperature = np.array([33966])

        pressure, temperature = calib.calibrate(raw_pressure, raw_temperature)

        assert pressure[0] == pytest.approx(100.805386352170, abs=1e-9)
        assert temperature[0] == pytest.approx(33.4321651817299, abs=1e-9)

    def test_calibrate_is_vectorized(self, calib: BMP280Calibration):
        raw_pressure = np.array([5540976, 5545168])
        raw_temperature = np.array([33966, 34026])

        pressure, temperature = calib.calibrate(raw_pressure, raw_temperature)

        assert len(pressure) == len(temperature) == 2
        assert pressure[0] == pytest.approx(100.805386352170, abs=1e-9)
        # The pressure rises slightly and the temperature with it
        assert pressure[1] > pressure[0]
        assert temperature[1] > temperature[0]


class TestBMP390Calibration:

    # Calibration block and raw readings taken from the test vector of the Shimmer
    # Java API reference implementation
    BLOCK = bytes(
        [
            0xE7,
            0x6B,
            0xF0,
            0x4A,
            0xF9,
            0xAB,
            0x1C,
            0x9B,
            0x15,
            0x06,
            0x01,
            0xD2,
            0x49,
            0x18,
            0x5F,
            0x03,
            0xFA,
            0x3A,
            0x0F,
            0x07,
            0xF5,
        ]
    )

    @pytest.fixture
    def calib(self) -> BMP390Calibration:
        return BMP390Calibration(self.BLOCK)

    def test_sensor(self, calib: BMP390Calibration):
        assert calib.sensor == EPressureSensor.BMP390

    def test_short_block(self):
        with pytest.raises(ValueError):
            BMP390Calibration(self.BLOCK[:-1])

    def test_quantized_coefficients(self, calib: BMP390Calibration):
        # The raw trim values are quantized by the powers of two given in the BMP390
        # datasheet
        assert calib.par_t1 == 0x6BE7 * 2.0**8
        assert calib.par_t2 == 0x4AF0 / 2.0**30
        assert calib.par_p1 == (0x1CAB - 2**14) / 2.0**20
        assert calib.par_p5 == 0x49D2 * 2.0**3

    def test_calibrate(self, calib: BMP390Calibration):
        raw_pressure = np.array([int.from_bytes(b"\x00\x0d\x64", "little")])
        raw_temperature = np.array([int.from_bytes(b"\x00\xba\x7f", "little")])

        pressure, temperature = calib.calibrate(raw_pressure, raw_temperature)

        # Plausibility: roughly sea-level pressure at room temperature
        assert pressure[0] == pytest.approx(100.911825, abs=1e-5)
        assert temperature[0] == pytest.approx(23.170170, abs=1e-5)


class TestBMP581Calibration:

    @pytest.fixture
    def calib(self) -> BMP581Calibration:
        return BMP581Calibration()

    def test_sensor(self, calib: BMP581Calibration):
        assert calib.sensor == EPressureSensor.BMP581

    def test_calibrate(self, calib: BMP581Calibration):
        # The BMP581 compensates on the chip, the readings only need scaling by
        # 2**6 for the pressure in Pa and 2**16 for the temperature in degrees
        pressure, temperature = calib.calibrate(
            np.array([100800 * 64]), np.array([25 * 65536])
        )

        assert pressure[0] == pytest.approx(100.8)
        assert temperature[0] == pytest.approx(25.0)


class TestBMP180Calibration:

    # Example coefficients from the BMP180 datasheet
    BLOCK = (
        np.array(
            [408, -72, -14383, 32741, 32757, 23153, 6190, 4, -32768, -8711, 2868],
            dtype=">i2",
        )
        .astype(">i2")
        .tobytes()
    )

    @pytest.fixture
    def calib(self) -> BMP180Calibration:
        return BMP180Calibration(self.BLOCK, oversampling=0)

    def test_sensor(self, calib: BMP180Calibration):
        assert calib.sensor == EPressureSensor.BMP180

    def test_short_block(self):
        with pytest.raises(ValueError):
            BMP180Calibration(self.BLOCK[:-1])

    def test_coefficients(self, calib: BMP180Calibration):
        assert calib.ac1 == 408
        assert calib.ac2 == -72
        assert calib.ac3 == -14383
        assert calib.ac4 == 32741
        assert calib.ac5 == 32757
        assert calib.ac6 == 23153
        assert calib.b1 == 6190
        assert calib.b2 == 4
        assert calib.mc == -8711
        assert calib.md == 2868

    def test_calibrate(self, calib: BMP180Calibration):
        # Readings from the worked example of the BMP180 datasheet, which yield 15
        # degrees Celsius and 69964 Pa. The device records the full 24bit pressure
        # register, which holds the pressure reading of the example in its upper
        # 16 bits at an oversampling setting of 0.
        raw_pressure = 23843 << 8
        pressure, temperature = calib.calibrate(
            np.array([raw_pressure]), np.array([27898])
        )

        assert temperature[0] == pytest.approx(15.0, abs=0.1)
        assert pressure[0] == pytest.approx(69.964, abs=0.05)

    @pytest.mark.parametrize("oversampling", [0, 1, 2, 3])
    def test_calibrate_with_oversampling(self, oversampling: int):
        # A higher oversampling setting adds significant bits to the reading but
        # leaves the register value of a given pressure unchanged. The same register
        # value must therefore yield the same pressure for every setting.
        calib = BMP180Calibration(self.BLOCK, oversampling=oversampling)

        pressure, _ = calib.calibrate(np.array([23843 << 8]), np.array([27898]))

        assert pressure[0] == pytest.approx(69.964, abs=0.05)
