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

import pytest

from pyshimmer import (
    EExpansionBoard,
    ExpansionBoard,
    EPressureSensor,
    FirmwareType,
    FirmwareVersion,
    Shimmer3RRevision,
    EChannelType,
    HardwareVersion,
)
from pyshimmer.dev.channels import ESensorGroup


class TestShimmer3RRevision:

    @pytest.fixture
    def revision(self) -> Shimmer3RRevision:
        return Shimmer3RRevision()

    def test_hardware_version(self, revision: Shimmer3RRevision):
        assert revision.hardware_version == HardwareVersion.SHIMMER3R

    def test_sd_file_layout(self, revision: Shimmer3RRevision):
        # The Shimmer3R header is 384 bytes long and holds the channel list at
        # offset 314
        assert revision.sd_header_len == 0x180
        assert revision.sd_channel_list_offset == 0x13A

        # Synchronized recordings are not supported yet
        assert revision.is_sd_sync_supported is False

    def test_all_channels_have_a_data_type(self, revision: Shimmer3RRevision):
        for ch in EChannelType:
            assert revision.get_channel_dtype(ch) is not None

    def test_high_g_accel_data_type(self, revision: Shimmer3RRevision):
        dtype = revision.get_channel_dtype(EChannelType.ACCEL_HG_X)

        assert dtype.size == 2
        assert dtype.bits == 12
        assert dtype.signed
        assert dtype.big_endian

    def test_alt_mag_data_type(self, revision: Shimmer3RRevision):
        dtype = revision.get_channel_dtype(EChannelType.MAG_WR_X)

        assert dtype.size == 2
        assert dtype.signed
        assert dtype.little_endian

    def test_pressure_data_types(self, revision: Shimmer3RRevision):
        # The Shimmer3R uses a different pressure sensor than the Shimmer3 which
        # reports both values as three byte little-endian words
        for ch in [EChannelType.TEMPERATURE, EChannelType.PRESSURE]:
            dtype = revision.get_channel_dtype(ch)

            assert dtype.size == 3
            assert not dtype.signed
            assert dtype.little_endian

    def test_triaxcal_sensors(self, revision: Shimmer3RRevision):
        assert set(revision.triaxcal_sensors) == {
            ESensorGroup.ACCEL_LN,
            ESensorGroup.ACCEL_WR,
            ESensorGroup.GYRO,
            ESensorGroup.MAG_REG,
            ESensorGroup.ACCEL_HG,
            ESensorGroup.MAG_WR,
        }

    def test_triaxcal_specs(self, revision: Shimmer3RRevision):
        # The kinematic calibration blocks are at the same offsets as on the
        # Shimmer3, the two additional sensors are stored past byte 256
        exp_offsets = {
            ESensorGroup.ACCEL_WR: 0x4C,
            ESensorGroup.GYRO: 0x61,
            ESensorGroup.MAG_REG: 0x76,
            ESensorGroup.ACCEL_LN: 0x8B,
            ESensorGroup.ACCEL_HG: 0x100,
            ESensorGroup.MAG_WR: 0x11D,
        }

        for sensor, exp_offset in exp_offsets.items():
            spec = revision.get_triaxcal_spec(sensor)

            assert spec.offset == exp_offset
            assert spec.offset_scaling == 1.0
            assert spec.alignment_scaling == 100.0

            # Only the gyroscope stores its gain scaled by a factor of 100
            exp_gain_scaling = 100.0 if sensor == ESensorGroup.GYRO else 1.0
            assert spec.gain_scaling == exp_gain_scaling

    def test_triaxcal_spec_for_unsupported_sensor(self, revision: Shimmer3RRevision):
        with pytest.raises(ValueError):
            revision.get_triaxcal_spec(ESensorGroup.GSR)

    def test_sensor_bit_assignment(self, revision: Shimmer3RRevision):
        # The high-g accelerometer and the alternative magnetometer reuse the bits of
        # the MPU9150 sensors of the Shimmer3
        bitfield = revision.sensors2bitfield(
            [ESensorGroup.ACCEL_HG, ESensorGroup.MAG_WR]
        )
        assert bitfield == 0x600000

        assert revision.bitfield2sensors(0x600000) == [
            ESensorGroup.ACCEL_HG,
            ESensorGroup.MAG_WR,
        ]

    def test_sensor_order_follows_channel_ids(self, revision: Shimmer3RRevision):
        sensors = [
            ESensorGroup.GYRO,
            ESensorGroup.MAG_REG,
            ESensorGroup.ACCEL_WR,
            ESensorGroup.ACCEL_LN,
        ]

        assert revision.sort_sensors(sensors) == [
            ESensorGroup.ACCEL_LN,
            ESensorGroup.ACCEL_WR,
            ESensorGroup.MAG_REG,
            ESensorGroup.GYRO,
        ]

    def test_pressure_sensor_bmp390(self, revision: Shimmer3RRevision):
        fw = (FirmwareType.LogAndStream, FirmwareVersion(1, 1, 14))

        for board in [
            # Older boards carry the BMP390
            ExpansionBoard(EExpansionBoard.SHIMMER3, 11, 1),
            ExpansionBoard(EExpansionBoard.EXG_UNIFIED, 8, 1),
            ExpansionBoard(EExpansionBoard.BR_AMP_UNIFIED, 4, 1),
            # The GSR+ board carries the BMP390 at revisions 7.0, 7.1, 8.0, and 8.1
            ExpansionBoard(EExpansionBoard.GSR_UNIFIED, 7, 1),
            ExpansionBoard(EExpansionBoard.GSR_UNIFIED, 8, 1),
            ExpansionBoard(EExpansionBoard.LOG_FILE, 255, 255),
        ]:
            assert (
                revision.get_pressure_sensor(board, *fw) == EPressureSensor.BMP390
            ), board

    def test_pressure_sensor_bmp581(self, revision: Shimmer3RRevision):
        fw = (FirmwareType.LogAndStream, FirmwareVersion(1, 1, 14))

        for board in [
            ExpansionBoard(EExpansionBoard.SHIMMER3, 11, 2),
            ExpansionBoard(EExpansionBoard.EXG_UNIFIED, 8, 2),
            ExpansionBoard(EExpansionBoard.BR_AMP_UNIFIED, 4, 2),
            # The GSR+ board carries the BMP581 within revision 7 from 7.2 onwards
            # and again from 8.2 onwards
            ExpansionBoard(EExpansionBoard.GSR_UNIFIED, 7, 2),
            ExpansionBoard(EExpansionBoard.GSR_UNIFIED, 8, 2),
            ExpansionBoard(EExpansionBoard.GSR_UNIFIED, 9, 0),
        ]:
            assert (
                revision.get_pressure_sensor(board, *fw) == EPressureSensor.BMP581
            ), board

    def test_pressure_sensor_bmp581_requires_firmware(
        self, revision: Shimmer3RRevision
    ):
        board = ExpansionBoard(EExpansionBoard.SHIMMER3, 11, 2)

        # The pre-compensated output only exists from LogAndStream v1.01.006 onwards
        assert (
            revision.get_pressure_sensor(
                board, FirmwareType.LogAndStream, FirmwareVersion(1, 1, 5)
            )
            == EPressureSensor.BMP390
        )
        assert (
            revision.get_pressure_sensor(
                board, FirmwareType.LogAndStream, FirmwareVersion(1, 1, 6)
            )
            == EPressureSensor.BMP581
        )
        assert (
            revision.get_pressure_sensor(
                board, FirmwareType.SDLog, FirmwareVersion(1, 1, 14)
            )
            == EPressureSensor.BMP390
        )

    def test_pressure_calib_blocks(self, revision: Shimmer3RRevision):
        assert revision.get_pressure_calib_blocks(EPressureSensor.BMP390) == [
            (0xA0, 21)
        ]
        # The BMP581 compensates on the chip and stores no parameters
        assert revision.get_pressure_calib_blocks(EPressureSensor.BMP581) == []

        with pytest.raises(ValueError):
            revision.get_pressure_calib_blocks(EPressureSensor.BMP280)
