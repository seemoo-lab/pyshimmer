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
from pyshimmer.dev.channels import EChannelType
from pyshimmer.dev.gsr import GSR_OPEN_CIRCUIT_LIMIT, calibrate_gsr, split_gsr_raw
from .reader_test_util import CONSENSYS_FIXTURES, ConsensysFixture

# Tolerance for a single channel value. Most channels agree exactly, the remainder
# differs only in the last bits of the floating point representation.
CHANNEL_ATOL = 1e-9

# Tolerance for a single timestamp in milliseconds, the unit of the reference export
TIMESTAMP_ATOL_MS = 1e-6

# The GSR channels whose value differs from the reference export where the
# electrodes read as open, see test_open_gsr_reads_open
GSR_OPEN_CHANNELS = (EChannelType.GSR_RESISTANCE, EChannelType.GSR_CONDUCTANCE)

GSR_FIXTURES = [f for f in CONSENSYS_FIXTURES if EChannelType.GSR_RAW in f.channels]


def fixture_id(fixture: ConsensysFixture) -> str:
    return fixture.name


def gsr_open_samples(reader: ShimmerReader) -> np.ndarray:
    """Mask of the samples whose GSR reading lies below the amplifier reference"""
    _, adc_value = split_gsr_raw(reader[EChannelType.GSR_RAW])
    return adc_value < GSR_OPEN_CIRCUIT_LIMIT


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

        assert bin_reader.gsr_range == case.gsr_range

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

            if channel in GSR_OPEN_CHANNELS:
                keep = ~gsr_open_samples(reader)
                expected, actual = expected[keep], actual[keep]

            np.testing.assert_allclose(
                actual,
                expected,
                rtol=0,
                atol=CHANNEL_ATOL,
                err_msg=f"channel {channel.name} does not match column {column}",
            )

    @pytest.mark.parametrize("gsr_case", GSR_FIXTURES, ids=fixture_id)
    def test_open_gsr_reads_open(self, gsr_case: ConsensysFixture):
        """GSR readings below the amplifier reference read as open electrodes

        Both recordings start with a few readings of zero. The reference tooling
        decodes them to a negative resistance and raises it to 8 kOhm, which
        reports the highest conductance the device can measure, 125 uS. We decode
        them as open instead, so they are left out of the comparison in
        test_channel_values.
        """
        with open(gsr_case.bin_path, "rb") as f:
            reader = ShimmerReader(bin_reader=ShimmerBinaryReader(f))
            reader.load_file_data()

        reference = gsr_case.read_reference()
        is_open = gsr_open_samples(reader)
        assert is_open.any()

        ref_conductance = reference[gsr_case.column_name("GSR_Skin_Conductance_CAL")]
        np.testing.assert_equal(ref_conductance.to_numpy()[is_open], 125.0)

        _, open_resistance, _ = calibrate_gsr((3 << 14) | GSR_OPEN_CIRCUIT_LIMIT)
        np.testing.assert_equal(
            reader[EChannelType.GSR_RESISTANCE][is_open], open_resistance
        )

    def test_every_reference_column_is_covered(self, case: ConsensysFixture):
        """The test case accounts for all channels of the reference export"""
        reference = case.read_reference()

        covered = {case.column_name(c) for c in case.columns}
        covered.add(case.column_name("Timestamp_Unix_CAL"))

        assert set(reference.columns) == covered
