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
import warnings
from io import BytesIO
from unittest import TestCase

import numpy as np
import pytest

from pyshimmer import EChannelType, ExGRegister, RevisionRegistry, ESensorGroup
from pyshimmer.dev.fw_version import FirmwareType, FirmwareVersion
from pyshimmer.dev.pressure import Bmp280Coefficients, EPressureSensor
from pyshimmer.dev.revisions import HardwareVersion
from pyshimmer.reader.reader_const import (
    DATA_LOG_OFFSET,
    ENABLED_SENSORS_OFFSET,
    EXP_BOARD_OFFSET,
    EXP_BOARD_LEN,
    FW_TYPE_OFFSET,
    HW_VERSION_OFFSET,
    PRESSURE_CALIB_OFFSET,
    PRESSURE_SENSOR_ID_OFFSET,
)
from pyshimmer.reader.shimmer_reader import ShimmerBinaryReader
from .reader_test_util import (
    get_binary_sample_fpath,
    get_synced_bin_vs_consensys_pair_fpath,
    get_ecg_sample,
    get_triaxcal_sample,
)


class ShimmerReaderTest(TestCase):

    def test_parsing_wo_sync(self):
        fpath = get_binary_sample_fpath()
        with open(fpath, "rb") as f:
            reader = ShimmerBinaryReader(f)

            exp_dr = 65
            exp_sensors = [
                ESensorGroup.ACCEL_LN,
                ESensorGroup.BATTERY,
                ESensorGroup.INT_CH_A1,
            ]
            exp_channels = [
                EChannelType.TIMESTAMP,
                EChannelType.ACCEL_LN_X,
                EChannelType.ACCEL_LN_Y,
                EChannelType.ACCEL_LN_Z,
                EChannelType.VBATT,
                EChannelType.INTERNAL_ADC_A1,
            ]

            revision = RevisionRegistry.REV_SHIMMER3
            sample_size = sum(
                [dt.size for dt in revision.get_channel_dtypes(exp_channels)]
            )
            samples_per_block = int(512 / sample_size)
            block_size = samples_per_block * sample_size

            self.assertEqual(reader.enabled_sensors, exp_sensors)
            self.assertEqual(reader.enabled_channels, exp_channels)
            self.assertEqual(reader.sample_rate, exp_dr)
            self.assertEqual(reader.has_global_clock, True)
            self.assertEqual(reader.has_sync, False)
            self.assertEqual(reader.is_sync_master, False)
            self.assertEqual(reader.samples_per_block, samples_per_block)
            self.assertEqual(reader.start_timestamp, 31291951)
            self.assertEqual(reader.block_size, block_size)
            self.assertEqual(
                reader.exg_reg1.binary, b"\x00\x80\x10\x00\x00\x00\x00\x00\x02\x01"
            )
            self.assertEqual(
                reader.exg_reg2.binary, b"\x00\x80\x10\x00\x00\x00\x00\x00\x02\x01"
            )

            data, _ = reader.read_data()
            ts = data[EChannelType.TIMESTAMP]

            # Sanity check on the timestamps: they should all be spaced equally apart
            # with a stride that is equal to the sampling rate.
            ts_diff = np.diff(ts)
            correct_diff = np.sum(ts_diff == exp_dr)
            self.assertTrue(correct_diff / len(ts_diff) > 0.98)

    def test_parsing_w_sync(self):
        fpath, _ = get_synced_bin_vs_consensys_pair_fpath()
        with open(fpath, "rb") as f:
            reader = ShimmerBinaryReader(f)

            exp_dr = 64
            exp_sensors = [ESensorGroup.INT_CH_A1]
            exp_channels = [EChannelType.TIMESTAMP, EChannelType.INTERNAL_ADC_A1]
            exp_offsets = np.array([372, 362, 364, 351])
            exp_sync_ts = np.array([3725366, 4071094, 4397558, 4724022])
            exp_exg_reg1 = ExGRegister(b"\x00\x80\x10\x00\x00\x00\x00\x00\x02\x01")
            exp_exg_reg2 = ExGRegister(b"\x00\x80\x10\x00\x00\x00\x00\x00\x02\x01")

            revision = RevisionRegistry.REV_SHIMMER3
            sample_size = sum(
                [dt.size for dt in revision.get_channel_dtypes(exp_channels)]
            )
            samples_per_block = int((512 - 9) / sample_size)
            block_size = samples_per_block * sample_size + 9

            self.assertEqual(reader.has_global_clock, True)
            self.assertEqual(reader.has_sync, True)
            self.assertEqual(reader.is_sync_master, False)
            self.assertEqual(reader.enabled_sensors, exp_sensors)
            self.assertEqual(reader.enabled_channels, exp_channels)
            self.assertEqual(reader.sample_rate, exp_dr)
            self.assertEqual(reader.samples_per_block, samples_per_block)
            self.assertEqual(reader.start_timestamp, 3085110)
            self.assertEqual(reader.block_size, block_size)

            self.assertEqual(reader.get_exg_reg(0), exp_exg_reg1)
            self.assertEqual(reader.get_exg_reg(1), exp_exg_reg2)
            self.assertEqual(reader.exg_reg1, exp_exg_reg1)
            self.assertEqual(reader.exg_reg2, exp_exg_reg2)

            samples, (off_index, sync_off) = reader.read_data()
            ts = samples[EChannelType.TIMESTAMP]

            np.testing.assert_equal(ts[off_index], exp_sync_ts)
            np.testing.assert_equal(sync_off, exp_offsets)

            # Sanity check on the timestamps: they should all be spaced equally apart
            # with a stride that is equal # to the sampling rate.
            ts = samples[EChannelType.TIMESTAMP]
            ts_diff = np.diff(ts)
            correct_diff = np.sum(ts_diff == exp_dr)
            self.assertTrue(correct_diff / len(ts_diff) > 0.98)

    def test_pressure_calibration(self):
        fpath = get_binary_sample_fpath()
        with open(fpath, "rb") as f:
            reader = ShimmerBinaryReader(f)

            # A GSR+ board of revision 3 carries a BMP280
            self.assertEqual(reader.expansion_board, (48, 3, 0))
            self.assertEqual(reader.pressure_oversampling, 0)

            calib = reader.pressure_calibration
            self.assertEqual(calib.sensor, EPressureSensor.BMP280)
            self.assertEqual(
                calib.binary,
                bytes.fromhex("036ddd653200cb92e4d6d00b1d1f64fff9ff8c3cf8c67017"),
            )
            self.assertFalse(calib.is_blank)
            self.assertEqual(
                calib.coefficients,
                Bmp280Coefficients(
                    dig_t1=27907,
                    dig_t2=26077,
                    dig_t3=50,
                    dig_p1=37579,
                    dig_p2=-10524,
                    dig_p3=3024,
                    dig_p4=7965,
                    dig_p5=-156,
                    dig_p6=-7,
                    dig_p7=15500,
                    dig_p8=-14600,
                    dig_p9=6000,
                ),
            )

    def test_pressure_calibration_blank(self):
        fpath, _ = get_synced_bin_vs_consensys_pair_fpath()
        with open(fpath, "rb") as f:
            reader = ShimmerBinaryReader(f)

            # The file was recorded by a firmware that does not store the pressure
            # calibration coefficients
            self.assertEqual(reader.pressure_calibration.sensor, EPressureSensor.BMP280)
            self.assertTrue(reader.pressure_calibration.is_blank)

            # The SDLog firmware leaves a 0x00 at the offset of the pressure sensor
            # ID, which must not be read as a BMP180
            self.assertEqual(reader.firmware_type, FirmwareType.SDLog)
            self.assertIsNone(reader.pressure_sensor_id)

    def test_firmware_version(self):
        fpath = get_binary_sample_fpath()
        with open(fpath, "rb") as f:
            reader = ShimmerBinaryReader(f)

            self.assertEqual(reader.hardware_version, HardwareVersion.SHIMMER3)
            self.assertEqual(reader.firmware_type, FirmwareType.LogAndStream)
            self.assertEqual(reader.firmware_version, FirmwareVersion(0, 11, 0))
            self.assertIsNone(reader.pressure_sensor_id)
            self.assertFalse(reader.pressure_sensor_inferred)

    def test_ecg_registers(self):
        fpath, _, _ = get_ecg_sample()
        with open(fpath, "rb") as f:
            reader = ShimmerBinaryReader(f)
            self.assertEqual(
                reader.exg_reg1.binary, b"\x03\xa8\x10\x49\x40\x23\x00\x00\x02\x03"
            )
            self.assertEqual(
                reader.exg_reg2.binary, b"\x03\xa0\x10\xc1\xc1\x00\x00\x00\x02\x01"
            )

    # noinspection PyMethodMayBeStatic
    def test_accel_ln_calib_data(self):
        exp_params = {
            ESensorGroup.ACCEL_LN: (
                np.array([2045, 2071, 2033]),
                np.diag([83, 83, 83]),
                np.array([[0.0, 1.0, 0.0], [1.0, 0.0, 0.02], [0.02, -0.01, -1.0]]),
            ),
            ESensorGroup.GYRO: (
                np.array([-123, -29, -35]),
                np.diag([56.68, 57.91, 59.21]),
                np.array([[0.0, 1.0, -0.02], [1.0, 0.0, 0.03], [-0.25, 0.01, -0.97]]),
            ),
        }

        fpath, _, _ = get_triaxcal_sample()
        with open(fpath, "rb") as f:
            reader = ShimmerBinaryReader(f)

            for sensor, (exp_offset, exp_gain, exp_alignment) in exp_params.items():
                offset, gain, alignment = reader.get_triaxcal_params(sensor)
                np.testing.assert_almost_equal(offset, exp_offset, decimal=10)
                np.testing.assert_almost_equal(gain, exp_gain, decimal=10)
                np.testing.assert_almost_equal(alignment, exp_alignment, decimal=10)


# Expansion boards for which the board revision implies a BMP180 or a BMP280
BOARD_BMP180 = (31, 5, 0)
BOARD_BMP280 = (48, 3, 0)


def create_header(
    sensor_id: int = 0xFF,
    exp_board: tuple[int, int, int] = BOARD_BMP280,
    hw_version: int = HardwareVersion.SHIMMER3,
    fw_type: int = FirmwareType.LogAndStream,
    fw_version: tuple[int, int, int] = (1, 1, 6),
    pressure_enabled: bool = True,
) -> BytesIO:
    """Create a file header from a real one, which records the given pressure sensor"""
    with open(get_binary_sample_fpath(), "rb") as f:
        header = bytearray(f.read(DATA_LOG_OFFSET))

    struct.pack_into(">H", header, HW_VERSION_OFFSET, hw_version)
    struct.pack_into(">HHBB", header, FW_TYPE_OFFSET, fw_type, *fw_version)
    header[EXP_BOARD_OFFSET : EXP_BOARD_OFFSET + EXP_BOARD_LEN] = bytes(exp_board)
    header[PRESSURE_SENSOR_ID_OFFSET] = sensor_id

    if pressure_enabled:
        rev = RevisionRegistry.REV_SHIMMER3
        sensor_bin = rev.serialize_sensorlist([ESensorGroup.PRESSURE])
        header[ENABLED_SENSORS_OFFSET : ENABLED_SENSORS_OFFSET + len(sensor_bin)] = (
            sensor_bin
        )

    return BytesIO(bytes(header))


def read_header(fp: BytesIO) -> tuple[ShimmerBinaryReader, list[str]]:
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        reader = ShimmerBinaryReader(fp)

    return reader, [str(warning.message) for warning in w]


class TestPressureSensorId:

    @pytest.mark.parametrize(
        "sensor_id,exp_board,sensor",
        [
            (0x00, BOARD_BMP180, EPressureSensor.BMP180),
            (0x01, BOARD_BMP280, EPressureSensor.BMP280),
        ],
    )
    def test_matches_board(
        self, sensor_id: int, exp_board: tuple[int, int, int], sensor: EPressureSensor
    ):
        reader, msgs = read_header(create_header(sensor_id, exp_board))

        assert reader.pressure_sensor_id == sensor_id
        assert reader.pressure_calibration.sensor == sensor
        assert not reader.pressure_sensor_inferred
        assert msgs == []

    @pytest.mark.parametrize(
        "sensor_id,exp_board,sensor",
        [
            (0x00, BOARD_BMP280, EPressureSensor.BMP180),
            (0x01, BOARD_BMP180, EPressureSensor.BMP280),
            (0x02, BOARD_BMP280, EPressureSensor.BMP390),
            (0x03, BOARD_BMP280, EPressureSensor.BMP581),
        ],
    )
    def test_overrides_board(
        self, sensor_id: int, exp_board: tuple[int, int, int], sensor: EPressureSensor
    ):
        reader, msgs = read_header(create_header(sensor_id, exp_board))

        assert reader.pressure_calibration.sensor == sensor
        assert not reader.pressure_sensor_inferred
        assert len(msgs) == 1
        assert "expansion board" in msgs[0]

    def test_coefficients(self):
        fp = create_header(0x02)
        header = fp.getvalue()
        reader, _ = read_header(fp)

        # The BMP390 occupies the first 21 bytes of the coefficient block
        exp_coeff = header[PRESSURE_CALIB_OFFSET : PRESSURE_CALIB_OFFSET + 21]
        assert reader.pressure_calibration.binary == exp_coeff

        reader, _ = read_header(create_header(0x03))
        assert reader.pressure_calibration.binary == b""

    def test_inferred(self):
        reader, msgs = read_header(create_header(0x83))

        assert reader.pressure_sensor_id == 0x83
        assert reader.pressure_calibration.sensor == EPressureSensor.BMP581
        assert reader.pressure_sensor_inferred
        assert any("chip ID" in m for m in msgs)

    def test_inferred_matches_board(self):
        reader, msgs = read_header(create_header(0x81))

        assert reader.pressure_calibration.sensor == EPressureSensor.BMP280
        assert reader.pressure_sensor_inferred
        assert len(msgs) == 1
        assert "chip ID" in msgs[0]

    @pytest.mark.parametrize("sensor_id", [0x04, 0x7D, 0x7E, 0x7F, 0x84, 0xFD])
    def test_unknown(self, sensor_id: int):
        # The sensor must not be taken from the expansion board instead
        reader, msgs = read_header(create_header(sensor_id))

        assert reader.pressure_sensor_id == sensor_id
        assert reader.pressure_calibration is None
        assert not reader.pressure_sensor_inferred
        assert len(msgs) == 1
        assert f"0x{sensor_id:02x}" in msgs[0]

    def test_no_sensor(self):
        reader, msgs = read_header(create_header(0xFE))

        assert reader.pressure_sensor_id == 0xFE
        assert reader.pressure_calibration is None
        assert len(msgs) == 1
        assert "no pressure sensor" in msgs[0]

    @pytest.mark.parametrize("sensor_id", [0x03, 0x04, 0x83, 0xFE])
    def test_no_warning_without_pressure_channels(self, sensor_id: int):
        reader, msgs = read_header(create_header(sensor_id, pressure_enabled=False))

        assert reader.pressure_sensor_id == sensor_id
        assert msgs == []

    @pytest.mark.parametrize(
        "exp_board,sensor",
        [
            (BOARD_BMP180, EPressureSensor.BMP180),
            (BOARD_BMP280, EPressureSensor.BMP280),
        ],
    )
    def test_unset(self, exp_board: tuple[int, int, int], sensor: EPressureSensor):
        reader, msgs = read_header(create_header(0xFF, exp_board))

        assert reader.pressure_sensor_id is None
        assert reader.pressure_calibration.sensor == sensor
        assert msgs == []

    @pytest.mark.parametrize(
        "hw_version,fw_type,fw_version,trusted",
        [
            # The Shimmer3 records the sensor since LogAndStream 1.1.6
            (HardwareVersion.SHIMMER3, FirmwareType.LogAndStream, (1, 1, 5), False),
            (HardwareVersion.SHIMMER3, FirmwareType.LogAndStream, (1, 1, 6), True),
            (HardwareVersion.SHIMMER3, FirmwareType.LogAndStream, (1, 1, 18), True),
            (HardwareVersion.SHIMMER3, FirmwareType.LogAndStream, (1, 2, 0), True),
            (HardwareVersion.SHIMMER3, FirmwareType.LogAndStream, (0, 16, 9), False),
            # Only the LogAndStream firmware records the sensor
            (HardwareVersion.SHIMMER3, FirmwareType.SDLog, (1, 1, 6), False),
            (HardwareVersion.SHIMMER3, FirmwareType.BtStream, (1, 1, 6), False),
            # The version numbers of the Shimmer3R overlap with those of the Shimmer3,
            # and the reader only supports the Shimmer3 anyway
            (HardwareVersion.SHIMMER3R, FirmwareType.LogAndStream, (1, 1, 6), False),
            (HardwareVersion.SHIMMER3R, FirmwareType.LogAndStream, (1, 1, 17), False),
            (HardwareVersion.SHIMMER3R, FirmwareType.LogAndStream, (1, 1, 18), False),
            (HardwareVersion.SHIMMER2R, FirmwareType.LogAndStream, (1, 1, 6), False),
        ],
    )
    def test_firmware_gate(
        self,
        hw_version: int,
        fw_type: int,
        fw_version: tuple[int, int, int],
        trusted: bool,
    ):
        fp = create_header(
            0x03, hw_version=hw_version, fw_type=fw_type, fw_version=fw_version
        )
        reader, _ = read_header(fp)

        assert reader.hardware_version == hw_version
        assert reader.firmware_type == fw_type
        assert reader.firmware_version == FirmwareVersion(*fw_version)

        if trusted:
            assert reader.pressure_sensor_id == 0x03
            assert reader.pressure_calibration.sensor == EPressureSensor.BMP581
        else:
            assert reader.pressure_sensor_id is None
            assert reader.pressure_calibration.sensor == EPressureSensor.BMP280
