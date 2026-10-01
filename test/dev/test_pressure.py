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
from __future__ import annotations

import struct

import numpy as np
import pytest

from pyshimmer.dev.channels import EChannelType
from pyshimmer.dev.pressure import (
    EPressureSensor,
    PressureCalibration,
    Bmp180Coefficients,
    Bmp280Coefficients,
    Bmp390Coefficients,
    compensate_bmp180,
    compensate_bmp280,
    compensate_bmp390,
    compensate_bmp581,
    prescale_raw_values,
    sign_extend_24,
    get_shimmer3_pressure_sensor,
)

# BST-BMP180-DS000 section 3.5, calculation example
BMP180_DATASHEET_COEFF = Bmp180Coefficients(
    ac1=408,
    ac2=-72,
    ac3=-14383,
    ac4=32741,
    ac5=32757,
    ac6=23153,
    b1=6190,
    b2=4,
    mb=-32768,
    mc=-8711,
    md=2868,
)
BMP180_DATASHEET_COEFF_BIN = struct.pack(
    ">hhhHHHhhhhh", 408, -72, -14383, 32741, 32757, 23153, 6190, 4, -32768, -8711, 2868
)
BMP180_DATASHEET_UT = 27898
BMP180_DATASHEET_UP = 23843

# BST-BMP280-DS001 sections 3.12 and 8.1, calculation example
BMP280_DATASHEET_COEFF = Bmp280Coefficients(
    dig_t1=27504,
    dig_t2=26435,
    dig_t3=-1000,
    dig_p1=36477,
    dig_p2=-10685,
    dig_p3=3024,
    dig_p4=2855,
    dig_p5=140,
    dig_p6=-7,
    dig_p7=15500,
    dig_p8=-14600,
    dig_p9=6000,
)
BMP280_DATASHEET_COEFF_BIN = struct.pack(
    "<HhhHhhhhhhhh",
    27504,
    26435,
    -1000,
    36477,
    -10685,
    3024,
    2855,
    140,
    -7,
    15500,
    -14600,
    6000,
)
BMP280_DATASHEET_ADC_T = 519888
BMP280_DATASHEET_ADC_P = 415148

# Coefficients and readings of a real BMP390
BMP390_COEFF_BIN = bytes(
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


class TestPressureSensor:

    @pytest.mark.parametrize(
        "sensor_id,sensor,size",
        [
            (0, EPressureSensor.BMP180, 22),
            (1, EPressureSensor.BMP280, 24),
            (2, EPressureSensor.BMP390, 21),
            (3, EPressureSensor.BMP581, 0),
        ],
    )
    def test_sensor_ids(self, sensor_id: int, sensor: EPressureSensor, size: int):
        assert EPressureSensor.from_sensor_id(sensor_id) == sensor
        assert sensor.coefficient_size == size

    def test_unknown_sensor_id(self):
        with pytest.raises(ValueError):
            EPressureSensor.from_sensor_id(4)

    @pytest.mark.parametrize(
        "board_id,rev,rev_special,sensor",
        [
            # Base IMU board
            (31, 5, 0, EPressureSensor.BMP180),
            (31, 6, 0, EPressureSensor.BMP280),
            # Proto3 Mini
            (36, 2, 0, EPressureSensor.BMP180),
            (36, 3, 0, EPressureSensor.BMP280),
            # Proto3 Deluxe
            (38, 2, 0, EPressureSensor.BMP180),
            (38, 3, 0, EPressureSensor.BMP280),
            # ExG unified
            (47, 2, 0, EPressureSensor.BMP180),
            (47, 3, 0, EPressureSensor.BMP280),
            # GSR+ unified
            (48, 2, 0, EPressureSensor.BMP180),
            (48, 3, 0, EPressureSensor.BMP280),
            # Bridge amplifier+ unified
            (49, 1, 0, EPressureSensor.BMP180),
            (49, 2, 0, EPressureSensor.BMP280),
            # Legacy ExG board
            (37, 9, 0, EPressureSensor.BMP180),
            # Any board on a newer base board
            (37, 1, 171, EPressureSensor.BMP280),
        ],
    )
    def test_shimmer3_pressure_sensor(
        self, board_id: int, rev: int, rev_special: int, sensor: EPressureSensor
    ):
        assert get_shimmer3_pressure_sensor(board_id, rev, rev_special) == sensor


class TestSignExtension:

    @pytest.mark.parametrize(
        "value,expected",
        [
            (0x000000, 0),
            (0x7FFFFF, 0x7FFFFF),
            (0x800000, -0x800000),
            (0xFFFFFF, -1),
            (0xFE5556, -109226),
            # Only the lower 24 bits are considered
            (0x1FE5556, -109226),
            # Values that are already sign-extended pass through unchanged
            (-1, -1),
            (-109226, -109226),
        ],
    )
    def test_sign_extend_24(self, value: int, expected: int):
        assert sign_extend_24(value) == expected

    def test_sign_extend_24_array(self):
        values = np.array([0x7FFFFF, 0x800000, 0xFFFFFF])
        np.testing.assert_equal(sign_extend_24(values), [0x7FFFFF, -0x800000, -1])


class TestCoefficients:

    def test_bmp180_coefficients(self):
        assert (
            Bmp180Coefficients.from_bytes(BMP180_DATASHEET_COEFF_BIN)
            == BMP180_DATASHEET_COEFF
        )

    def test_bmp180_coefficients_byte_order(self):
        # Big endian, AC4 to AC6 are unsigned
        coeff_bin = bytes([0xFF, 0xFE] * 3 + [0xFF, 0xFE] * 3 + [0x00, 0x01] * 5)
        c = Bmp180Coefficients.from_bytes(coeff_bin)

        assert (c.ac1, c.ac2, c.ac3) == (-2, -2, -2)
        assert (c.ac4, c.ac5, c.ac6) == (0xFFFE, 0xFFFE, 0xFFFE)
        assert (c.b1, c.b2, c.mb, c.mc, c.md) == (1, 1, 1, 1, 1)

    def test_bmp280_coefficients(self):
        assert (
            Bmp280Coefficients.from_bytes(BMP280_DATASHEET_COEFF_BIN)
            == BMP280_DATASHEET_COEFF
        )

    def test_bmp280_coefficients_byte_order(self):
        # Little endian, dig_T1 and dig_P1 are unsigned
        c = Bmp280Coefficients.from_bytes(bytes([0xFE, 0xFF] * 12))

        assert c.dig_t1 == 0xFFFE
        assert c.dig_p1 == 0xFFFE
        assert (c.dig_t2, c.dig_t3) == (-2, -2)
        assert (c.dig_p2, c.dig_p5, c.dig_p9) == (-2, -2, -2)

    def test_bmp390_coefficients(self):
        c = Bmp390Coefficients.from_bytes(BMP390_COEFF_BIN)

        assert c.par_t1 == 7071488
        assert c.par_t2 == pytest.approx(0.00001786649227142334, rel=1e-15)
        assert c.par_t3 == pytest.approx(-0.000000000000024868995751603507, rel=1e-15)
        assert c.par_p1 == pytest.approx(-0.0086259841918945312, rel=1e-15)
        assert c.par_p2 == pytest.approx(-0.000020215287804603577, rel=1e-15)
        assert c.par_p3 == pytest.approx(0.0000000013969838619232178, rel=1e-15)
        assert c.par_p4 == pytest.approx(0.0000000000072759576141834259, rel=1e-15)
        assert c.par_p5 == 151184
        assert c.par_p6 == 380.375
        assert c.par_p7 == 0.01171875
        assert c.par_p8 == -0.00018310546875
        assert c.par_p9 == pytest.approx(0.000000000013848477919964353, rel=1e-15)
        assert c.par_p10 == pytest.approx(0.000000000000024868995751603507, rel=1e-15)
        assert c.par_p11 == pytest.approx(
            -0.00000000000000000029815559743351372, rel=1e-15
        )


class TestCompensation:

    def test_bmp180_datasheet_example(self):
        p, t = compensate_bmp180(
            BMP180_DATASHEET_UP, BMP180_DATASHEET_UT, BMP180_DATASHEET_COEFF, 0
        )

        # The datasheet uses integer arithmetic and arrives at 15.0 degrees Celsius
        # and 69964 Pa. The floating-point version skips the integer truncation and
        # therefore deviates slightly.
        assert t == pytest.approx(15.0, abs=0.1)
        assert p == pytest.approx(69964, abs=5)

        assert t == pytest.approx(15.047124207544877, rel=1e-12)
        assert p == pytest.approx(69960.65854994976, rel=1e-12)

    def test_bmp180_invalid_oversampling(self):
        with pytest.raises(ValueError):
            compensate_bmp180(0, 0, BMP180_DATASHEET_COEFF, 4)

    def test_bmp280_datasheet_example(self):
        p, t = compensate_bmp280(
            BMP280_DATASHEET_ADC_P, BMP280_DATASHEET_ADC_T, BMP280_DATASHEET_COEFF
        )

        assert t == pytest.approx(25.08, abs=0.005)
        assert p == pytest.approx(100653.27, abs=0.005)

    @pytest.mark.parametrize(
        "raw_p_bin,raw_t_bin,exp_p,exp_t",
        [
            (b"\x00\x0d\x64", b"\x00\xba\x7f", 100911.8245, 23.1702),
            (b"\x00\x17\x64", b"\x00\xcf\x7f", 100912.8176, 23.2659),
        ],
    )
    def test_bmp390(self, raw_p_bin: bytes, raw_t_bin: bytes, exp_p: float, exp_t):
        coeff = Bmp390Coefficients.from_bytes(BMP390_COEFF_BIN)
        up = int.from_bytes(raw_p_bin, "little")
        ut = int.from_bytes(raw_t_bin, "little")

        p, t = compensate_bmp390(up, ut, coeff)
        assert round(p, 4) == exp_p
        assert round(t, 4) == exp_t

    def test_bmp390_limits(self):
        coeff = Bmp390Coefficients.from_bytes(BMP390_COEFF_BIN)

        # Bosch clamps the results to -40 to 85 degrees Celsius and 30 to 125 kPa
        assert compensate_bmp390(0, 0, coeff) == (125000.0, -40.0)
        assert compensate_bmp390(0xFFFFFF, 0xFFFFFF, coeff) == (30000.0, 85.0)

    @pytest.mark.parametrize(
        "up,exp_p",
        [
            (6400000, 100000.0),
            (0xFFFFFF, 262143.984375),
            (0, 0.0),
        ],
    )
    def test_bmp581_pressure(self, up: int, exp_p: float):
        p, _ = compensate_bmp581(up, 0)
        assert p == exp_p

    @pytest.mark.parametrize(
        "ut,exp_t",
        [
            (1638400, 25.0),
            (1600000, 24.4140625),
            (0x7FFFFF, 127.9999847),
            (0xFFFFFF, -1 / 65536),
            (0xFE5556, -1.6666565),
            (0x800000, -128.0),
        ],
    )
    def test_bmp581_temperature(self, ut: int, exp_t: float):
        _, t = compensate_bmp581(0, ut)
        assert t == pytest.approx(exp_t, abs=1e-7)

    def test_array_input(self):
        up = np.array([BMP280_DATASHEET_ADC_P] * 3)
        ut = np.array([BMP280_DATASHEET_ADC_T] * 3)

        p, t = compensate_bmp280(up, ut, BMP280_DATASHEET_COEFF)
        assert isinstance(p, np.ndarray) and isinstance(t, np.ndarray)
        np.testing.assert_allclose(p, 100653.27, atol=0.005)
        np.testing.assert_allclose(t, 25.08, atol=0.005)

        p, t = compensate_bmp581(np.array([6400000, 0xFFFFFF]), np.array([0, 0xFFFFFF]))
        np.testing.assert_equal(p, [100000.0, 262143.984375])
        np.testing.assert_equal(t, [0.0, -1 / 65536])

    def test_scalar_output(self):
        p, t = compensate_bmp581(6400000, 1638400)
        assert type(p) is float and type(t) is float


class TestPrescaling:

    def test_bmp180(self):
        for oss in range(4):
            up, ut = prescale_raw_values(
                EPressureSensor.BMP180, 0x5D2300 * 4, 27898, oss
            )
            assert up == 0x5D2300 * 4 / 2 ** (8 - oss)
            assert ut == 27898

    def test_bmp280(self):
        up, ut = prescale_raw_values(EPressureSensor.BMP280, 0x655AC0, 0x7EED)
        assert up == 0x655AC
        assert ut == 0x7EED0

    @pytest.mark.parametrize("sensor", [EPressureSensor.BMP390, EPressureSensor.BMP581])
    def test_shimmer3r(self, sensor: EPressureSensor):
        assert prescale_raw_values(sensor, 0x640D00, 0x7FBA00) == (0x640D00, 0x7FBA00)


class TestPressureCalibration:

    @pytest.mark.parametrize(
        "sensor,size", [(0, 22), (1, 24), (2, 21), (3, 0)], ids=lambda x: str(x)
    )
    def test_length_validation(self, sensor: int, size: int):
        PressureCalibration(EPressureSensor(sensor), bytes(range(1, size + 1)))

        with pytest.raises(ValueError):
            PressureCalibration(EPressureSensor(sensor), bytes(size + 1))

        if size > 0:
            with pytest.raises(ValueError):
                PressureCalibration(EPressureSensor(sensor), bytes(size - 1))

    def test_properties(self):
        calib = PressureCalibration(EPressureSensor.BMP390, BMP390_COEFF_BIN)
        assert calib.sensor == EPressureSensor.BMP390
        assert calib.binary == BMP390_COEFF_BIN
        assert calib.coefficients == Bmp390Coefficients.from_bytes(BMP390_COEFF_BIN)
        assert not calib.is_blank

        calib = PressureCalibration(EPressureSensor.BMP581, b"")
        assert calib.sensor == EPressureSensor.BMP581
        assert calib.binary == b""
        assert calib.coefficients is None
        assert not calib.is_blank

    def test_equality(self):
        a = PressureCalibration(EPressureSensor.BMP390, BMP390_COEFF_BIN)
        b = PressureCalibration(EPressureSensor.BMP390, BMP390_COEFF_BIN)
        c = PressureCalibration(EPressureSensor.BMP390, bytes(21))

        assert a == b
        assert a != c
        assert a != PressureCalibration(EPressureSensor.BMP581, b"")

    @pytest.mark.parametrize("fill", [0x00, 0x01, 0xFF])
    def test_blank(self, fill: int):
        calib = PressureCalibration(EPressureSensor.BMP280, bytes([fill] * 24))
        assert calib.is_blank

        with pytest.raises(ValueError):
            calib.compensate(0, 0)

    def test_compensate_bmp180(self):
        calib = PressureCalibration(EPressureSensor.BMP180, BMP180_DATASHEET_COEFF_BIN)

        for oss in range(4):
            # The Shimmer transmits the left-aligned 24-bit reading
            raw_p = BMP180_DATASHEET_UP << (8 - oss)
            p, t = calib.compensate(raw_p, BMP180_DATASHEET_UT, oss)
            exp_p, exp_t = compensate_bmp180(
                BMP180_DATASHEET_UP, BMP180_DATASHEET_UT, BMP180_DATASHEET_COEFF, oss
            )

            assert p == exp_p
            assert t == exp_t

    def test_compensate_bmp280(self):
        calib = PressureCalibration(EPressureSensor.BMP280, BMP280_DATASHEET_COEFF_BIN)

        # The Shimmer3 omits the four lowest bits of the temperature reading and
        # appends four zero bits to the pressure reading
        raw_p = BMP280_DATASHEET_ADC_P << 4
        raw_t = BMP280_DATASHEET_ADC_T >> 4
        p, t = calib.compensate(raw_p, raw_t)

        assert t == pytest.approx(25.08, abs=0.005)
        assert p == pytest.approx(100653.27, abs=0.005)

    def test_compensate_bmp390(self):
        calib = PressureCalibration(EPressureSensor.BMP390, BMP390_COEFF_BIN)
        p, t = calib.compensate(6556928, 8370688)

        assert round(p, 4) == 100911.8245
        assert round(t, 4) == 23.1702

    def test_compensate_bmp581(self):
        calib = PressureCalibration(EPressureSensor.BMP581, b"")

        p, t = calib.compensate(6400000, 0xFE5556)
        assert p == 100000.0
        assert t == pytest.approx(-1.6666565, abs=1e-7)

    def test_compensate_channels(self):
        calib = PressureCalibration(EPressureSensor.BMP581, b"")
        channels = {
            EChannelType.PRESSURE: np.array([6400000, 0xFFFFFF]),
            EChannelType.TEMPERATURE: np.array([1638400, 0x800000]),
        }

        p, t = calib.compensate_channels(channels)
        np.testing.assert_equal(p, [100000.0, 262143.984375])
        np.testing.assert_equal(t, [25.0, -128.0])
