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
"""Comparison of the reader against the Shimmer reference tooling

Each test case is a binary data file paired with an export of the same recording
produced by the Shimmer reference tooling. Where the synthetic test files elsewhere
in this test suite only pin down our reading of the documented file format, these
compare the reader against a known-good implementation on data written by an actual
device.
"""

from __future__ import annotations

import numpy as np
import pytest

from pyshimmer import ShimmerBinaryReader, ShimmerReader
from .reader_test_util import CONSENSYS_FIXTURES, ConsensysFixture

# Tolerance for a single channel value. Most channels agree exactly, the remainder
# differs only in the last bits of the floating point representation.
CHANNEL_ATOL = 1e-9

# Tolerance for a single timestamp in milliseconds, the unit of the reference export
TIMESTAMP_ATOL_MS = 1e-6


def fixture_id(fixture: ConsensysFixture) -> str:
    return fixture.name


@pytest.fixture(params=CONSENSYS_FIXTURES, ids=fixture_id)
def case(request) -> ConsensysFixture:
    return request.param


@pytest.fixture
def bin_reader(case: ConsensysFixture) -> ShimmerBinaryReader:
    with open(case.bin_path, "rb") as f:
        yield ShimmerBinaryReader(f)


class TestConsensysReference:

    def test_device_details(
        self, case: ConsensysFixture, bin_reader: ShimmerBinaryReader
    ):
        """The device properties are read from the file header"""
        assert bin_reader.hardware_revision.hardware_version == case.hw_version
        assert bin_reader.firmware_type == case.fw_type

        fw = bin_reader.firmware_version
        assert (fw.major, fw.minor, fw.rel) == case.fw_version

        board = bin_reader.expansion_board
        assert (board.board_id, board.rev, board.rev_special) == case.exp_board

        # The pressure sensor model follows from the hardware revision, the
        # expansion board, and the firmware version
        assert bin_reader.pressure_sensor == case.pressure_sensor

    def test_channel_layout(
        self, case: ConsensysFixture, bin_reader: ShimmerBinaryReader
    ):
        """The set and order of channels matches the channel list of the header"""
        reader = ShimmerReader(bin_reader=bin_reader)
        reader.load_file_data()

        assert tuple(reader.channels) == case.channels
        assert tuple(reader.derived_channels) == case.derived_channels
        assert reader.sample_rate == pytest.approx(case.sample_rate)

    def test_sample_count(
        self, case: ConsensysFixture, bin_reader: ShimmerBinaryReader
    ):
        """No sample is lost or invented relative to the reference export"""
        reader = ShimmerReader(bin_reader=bin_reader)
        reader.load_file_data()

        reference = case.read_reference()

        assert len(reader.timestamp) == case.num_samples
        assert len(reference) == case.num_samples

    def test_timestamps(self, case: ConsensysFixture, bin_reader: ShimmerBinaryReader):
        """The absolute timestamps match the reference export"""
        reader = ShimmerReader(bin_reader=bin_reader)
        reader.load_file_data()

        reference = case.read_reference()
        expected = reference[case.column_name("Timestamp_Unix_CAL")].to_numpy()

        # The reference export reports the timestamps in milliseconds
        actual = reader.timestamp * 1000.0

        np.testing.assert_allclose(actual, expected, rtol=0, atol=TIMESTAMP_ATOL_MS)

    def test_channel_values(
        self, case: ConsensysFixture, bin_reader: ShimmerBinaryReader
    ):
        """Every channel of the reference export matches our calibrated output"""
        reader = ShimmerReader(bin_reader=bin_reader)
        reader.load_file_data()

        reference = case.read_reference()

        for column, (channel, scale) in case.columns.items():
            expected = reference[case.column_name(column)].to_numpy()
            actual = reader[channel] * scale

            np.testing.assert_allclose(
                actual,
                expected,
                rtol=0,
                atol=CHANNEL_ATOL,
                err_msg=f"channel {channel.name} does not match column {column}",
            )

    def test_every_reference_column_is_covered(self, case: ConsensysFixture):
        """The test case accounts for all channels of the reference export"""
        reference = case.read_reference()

        covered = {case.column_name(c) for c in case.columns}
        covered.add(case.column_name("Timestamp_Unix_CAL"))

        assert set(reference.columns) == covered
