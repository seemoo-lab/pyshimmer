# pyshimmer - API for Shimmer sensor devices
# Copyright (C) 2025  Lukas Magel

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

import itertools

import numpy as np
import pytest

from pyshimmer import (
    EExpansionBoard,
    ExpansionBoard,
    EPressureSensor,
    FirmwareType,
    FirmwareVersion,
    Shimmer3Revision,
    EChannelType,
)
from pyshimmer.dev.channels import ESensorGroup


class TestShimmer3Revision:

    @pytest.fixture
    def revision(self) -> Shimmer3Revision:
        return Shimmer3Revision()

    def test_sr2dr(self, revision: Shimmer3Revision):
        r = revision.sr2dr(1024.0)
        assert r == 32

        r = revision.sr2dr(500.0)
        assert r == 66

    def test_dr2sr(self, revision: Shimmer3Revision):
        r = revision.dr2sr(65)
        assert r == pytest.approx(504, abs=0.5)

        r = revision.dr2sr(32)
        assert r == 1024.0

        r = revision.dr2sr(64)
        assert r == 512.0

    def test_sec2ticks(self, revision: Shimmer3Revision):
        r = revision.sec2ticks(1.0)
        assert r == 32768

        r = revision.sec2ticks(np.array([1.0, 2.0]))
        np.testing.assert_array_equal(r, np.array([32768, 65536]))

    def test_ticks2sec(self, revision: Shimmer3Revision):
        r = revision.ticks2sec(32768)
        assert r == 1.0

        r = revision.ticks2sec(65536)
        assert r == 2.0

        i = np.array([32768, 65536])
        r = revision.ticks2sec(i)
        np.testing.assert_array_equal(r, np.array([1.0, 2.0]))

    def test_get_channel_dtypes(self, revision: Shimmer3Revision):
        r = revision.get_channel_dtypes([])
        assert r == []

        r = revision.get_channel_dtypes(())
        assert r == []

        r = revision.get_channel_dtypes(
            [EChannelType.INTERNAL_ADC_A0, EChannelType.INTERNAL_ADC_A0]
        )
        assert len(r) == 2
        assert r[0] == r[1]

        channels = [EChannelType.INTERNAL_ADC_A1, EChannelType.GYRO_Y]
        r = revision.get_channel_dtypes(channels)

        assert len(r) == 2
        first, second = r

        assert first.size == 2
        assert first.little_endian is True
        assert first.signed is False

        assert second.size == 2
        assert second.little_endian is False
        assert second.signed is True

    def test_channel_dtype_assignment(self, revision: Shimmer3Revision):
        # Derived channels are calculated rather than read from the data stream, so
        # they do not possess a binary data type
        for channel in EChannelType:
            if channel.is_derived:
                continue

            r = revision.get_channel_dtypes([channel])
            assert len(r) > 0

    def test_get_enabled_channels(self, revision: Shimmer3Revision):
        r = revision.get_enabled_channels([])
        assert r == []

        r = revision.get_enabled_channels(())
        assert r == []

        r = revision.get_enabled_channels(
            [ESensorGroup.PRESSURE, ESensorGroup.ACCEL_LN]
        )

        assert r == [
            EChannelType.TEMPERATURE,
            EChannelType.PRESSURE,
            EChannelType.ACCEL_LN_X,
            EChannelType.ACCEL_LN_Y,
            EChannelType.ACCEL_LN_Z,
        ]

    def test_sensor_group_assignment(self, revision: Shimmer3Revision):
        for group in ESensorGroup:
            r = revision.get_enabled_channels([group])

            if group != ESensorGroup.TEMP:
                assert len(r) > 0

    def test_sensor_list_to_bitfield(self, revision: Shimmer3Revision):
        r = revision.sensors2bitfield((ESensorGroup.ACCEL_LN, ESensorGroup.EXT_CH_A1))
        assert r == 0x81

        r = revision.sensors2bitfield((ESensorGroup.STRAIN, ESensorGroup.INT_CH_A1))
        assert r == 0x8100

        r = revision.sensors2bitfield((ESensorGroup.INT_CH_A2, ESensorGroup.TEMP))
        assert r == 0x820000

    def test_bitfield_to_sensors(self, revision: Shimmer3Revision):
        r = revision.bitfield2sensors(0x81)
        assert r == [ESensorGroup.ACCEL_LN, ESensorGroup.EXT_CH_A1]

        r = revision.bitfield2sensors(0x8100)
        assert r == [ESensorGroup.INT_CH_A1, ESensorGroup.STRAIN]

        r = revision.bitfield2sensors(0x820000)
        assert r == [
            ESensorGroup.INT_CH_A2,
            ESensorGroup.TEMP,
        ]

    def test_sensor_bit_assignment_uniqueness(self, revision: Shimmer3Revision):
        for group1, group2 in itertools.product(ESensorGroup, ESensorGroup):
            if group1 == group2:
                continue

            bitfield1 = revision.sensors2bitfield([group1])
            bitfield2 = revision.sensors2bitfield([group2])
            assert bitfield1 != bitfield2

    def test_serialize_sensorlist(self, revision: Shimmer3Revision):
        r = revision.serialize_sensorlist([])
        assert r == b"\x00\x00\x00"

        r = revision.serialize_sensorlist([ESensorGroup.GSR, ESensorGroup.BATTERY])
        assert r == b"\x04\x20\x00"

    def test_deserialize_sensorlist(self, revision: Shimmer3Revision):
        r = revision.deserialize_sensorlist(b"\x00\x00\x00")
        assert r == []

        r = revision.deserialize_sensorlist(b"\x01\x80\x01")
        assert r == [
            ESensorGroup.EXT_CH_A1,
            ESensorGroup.STRAIN,
        ]

    def test_serialize_deserialize(self, revision: Shimmer3Revision):
        for group in ESensorGroup:
            bitfield = revision.serialize_sensorlist([group])
            group_deserialized = revision.deserialize_sensorlist(bitfield)
            assert [group] == group_deserialized

    def test_sort_sensors(self, revision: Shimmer3Revision):
        sensors = [ESensorGroup.BATTERY, ESensorGroup.ACCEL_LN]
        expected = [ESensorGroup.ACCEL_LN, ESensorGroup.BATTERY]
        r = revision.sort_sensors(sensors)
        assert r == expected

        sensors = [
            ESensorGroup.EXT_CH_A2,
            ESensorGroup.MAG_WR,
            ESensorGroup.ACCEL_LN,
            ESensorGroup.EXT_CH_A2,
        ]
        expected = [
            ESensorGroup.ACCEL_LN,
            ESensorGroup.EXT_CH_A2,
            ESensorGroup.EXT_CH_A2,
            ESensorGroup.MAG_WR,
        ]
        r = revision.sort_sensors(sensors)
        assert r == expected

    def test_unwrap_device_timestamps(self, revision: Shimmer3Revision):
        ts_wrapped = np.array([0, 1, 2, 2**24 - 1, 0, 2**24])
        expected = np.array([0, 1, 2, 2**24 - 1, 2**24, 2 * 2**24])
        actual = revision.unwrap_device_timestamps(ts_wrapped)
        np.testing.assert_equal(actual, expected)

        ts_wrapped = np.array([0, 10, 20, 30, 5, 15, 25, 35])
        expected = np.array(
            [0, 10, 20, 30, 5 + 2**24, 15 + 2**24, 25 + 2**24, 35 + 2**24]
        )
        actual = revision.unwrap_device_timestamps(ts_wrapped)
        np.testing.assert_equal(actual, expected)

    def test_sd_file_layout(self, revision: Shimmer3Revision):
        # The Shimmer3 header is 256 bytes long and does not record a channel list,
        # the channels are derived from the enabled sensors instead
        assert revision.sd_header_len == 0x100
        assert revision.sd_channel_list_offset is None
        assert revision.is_sd_sync_supported is True

    def test_triaxcal_specs(self, revision: Shimmer3Revision):
        assert set(revision.triaxcal_sensors) == {
            ESensorGroup.ACCEL_LN,
            ESensorGroup.ACCEL_WR,
            ESensorGroup.GYRO,
            ESensorGroup.MAG_REG,
        }

        exp_offsets = {
            ESensorGroup.ACCEL_WR: 0x4C,
            ESensorGroup.GYRO: 0x61,
            ESensorGroup.MAG_REG: 0x76,
            ESensorGroup.ACCEL_LN: 0x8B,
        }

        for sensor, exp_offset in exp_offsets.items():
            spec = revision.get_triaxcal_spec(sensor)

            assert spec.offset == exp_offset
            assert spec.offset_scaling == 1.0
            assert spec.alignment_scaling == 100.0

            exp_gain_scaling = 100.0 if sensor == ESensorGroup.GYRO else 1.0
            assert spec.gain_scaling == exp_gain_scaling

    def test_triaxcal_spec_for_unsupported_sensor(self, revision: Shimmer3Revision):
        # The Shimmer3 does not record calibration data for the MPU9150 sensors
        with pytest.raises(ValueError):
            revision.get_triaxcal_spec(ESensorGroup.ACCEL_HG)

    def test_pressure_sensor_bmp180(self, revision: Shimmer3Revision):
        # Older expansion boards carry the BMP180
        for board in [
            ExpansionBoard(EExpansionBoard.SHIMMER3, 5, 0),
            ExpansionBoard(EExpansionBoard.GSR_UNIFIED, 2, 0),
            ExpansionBoard(EExpansionBoard.EXG_UNIFIED, 1, 0),
            ExpansionBoard(EExpansionBoard.LOG_FILE, 255, 255),
        ]:
            sensor = revision.get_pressure_sensor(
                board, FirmwareType.LogAndStream, FirmwareVersion(0, 15, 4)
            )
            assert sensor == EPressureSensor.BMP180, board

    def test_pressure_sensor_bmp280(self, revision: Shimmer3Revision):
        # Boards with the newer IMU set carry the BMP280
        for board in [
            ExpansionBoard(EExpansionBoard.SHIMMER3, 6, 0),
            ExpansionBoard(EExpansionBoard.GSR_UNIFIED, 3, 0),
            ExpansionBoard(EExpansionBoard.GSR_UNIFIED, 4, 2),
            ExpansionBoard(EExpansionBoard.BR_AMP_UNIFIED, 3, 0),
            # Any board attached to a new IMU base board
            ExpansionBoard(EExpansionBoard.LOG_FILE, 0, 171),
        ]:
            sensor = revision.get_pressure_sensor(
                board, FirmwareType.LogAndStream, FirmwareVersion(0, 15, 4)
            )
            assert sensor == EPressureSensor.BMP280, board
