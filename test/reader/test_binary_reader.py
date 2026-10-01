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

import io
from unittest import TestCase

import numpy as np

from pyshimmer import (
    EChannelType,
    ExGRegister,
    HardwareVersion,
    RevisionRegistry,
    ESensorGroup,
)
from pyshimmer.dev.gsr import GSR_RANGE_AUTO
from pyshimmer.reader.shimmer_reader import ShimmerBinaryReader
from .reader_test_util import (
    build_shimmer3r_file,
    encode_triaxcal_block,
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


class Shimmer3RBinaryReaderTest(TestCase):
    """Tests for the Shimmer3R binary file format

    The binary files used here are synthesized from the header layout documented by
    the Java reference implementation. They verify that this API implements that
    layout, but they cannot confirm the layout itself. Regression tests against a file
    recorded by an actual Shimmer3R are still needed.
    """

    @staticmethod
    def _open(content: bytes, **kwargs) -> ShimmerBinaryReader:
        return ShimmerBinaryReader(io.BytesIO(content), **kwargs)

    def test_hardware_version_detection(self):
        content = build_shimmer3r_file(channels=[EChannelType.VBATT], samples=[])
        reader = self._open(content)

        self.assertEqual(
            reader.hardware_revision.hardware_version, HardwareVersion.SHIMMER3R
        )
        self.assertIs(reader.hardware_revision, RevisionRegistry.REV_SHIMMER3R)

    def test_unknown_hardware_version_is_rejected(self):
        content = bytearray(
            build_shimmer3r_file(channels=[EChannelType.VBATT], samples=[])
        )
        content[0x1E:0x20] = b"\x00\x63"

        with self.assertRaises(ValueError):
            self._open(bytes(content))

    def test_explicit_hardware_version_overrides_header(self):
        content = bytearray(
            build_shimmer3r_file(channels=[EChannelType.VBATT], samples=[])
        )
        content[0x1E:0x20] = b"\x00\x63"

        reader = self._open(bytes(content), hw_version=HardwareVersion.SHIMMER3R)
        self.assertEqual(
            reader.hardware_revision.hardware_version, HardwareVersion.SHIMMER3R
        )

    def test_channels_are_read_from_header(self):
        # Deliberately ordered differently from the sensor order of the revision to
        # show that the header list takes precedence
        channels = [
            EChannelType.GYRO_X,
            EChannelType.ACCEL_LN_X,
            EChannelType.VBATT,
        ]
        content = build_shimmer3r_file(
            channels=channels,
            samples=[],
            sensors=[
                ESensorGroup.ACCEL_LN,
                ESensorGroup.GYRO,
                ESensorGroup.BATTERY,
            ],
        )
        reader = self._open(content)

        self.assertEqual(reader.enabled_channels, [EChannelType.TIMESTAMP] + channels)
        self.assertEqual(
            reader.enabled_sensors,
            [ESensorGroup.ACCEL_LN, ESensorGroup.BATTERY, ESensorGroup.GYRO],
        )

    def test_data_starts_after_the_384_byte_header(self):
        channels = [EChannelType.VBATT]
        samples = [[100 * i, i] for i in range(1, 5)]

        content = build_shimmer3r_file(
            channels=channels, samples=samples, sample_rate=100, start_ts=4242
        )

        # Three byte timestamp plus a two byte battery channel per sample
        self.assertEqual(len(content), 0x180 + 4 * 5)
        self.assertEqual(RevisionRegistry.REV_SHIMMER3R.sd_header_len, 0x180)

        reader = self._open(content)
        self.assertEqual(reader.sample_rate, 100)
        self.assertEqual(reader.start_timestamp, 4242)
        self.assertEqual(reader.has_sync, False)

        data, sync = reader.read_data()
        np.testing.assert_equal(
            data[EChannelType.TIMESTAMP], np.array([100, 200, 300, 400])
        )
        np.testing.assert_equal(data[EChannelType.VBATT], np.array([1, 2, 3, 4]))
        self.assertEqual(sync, ((), ()))

    def test_high_g_accel_and_alt_mag_channels(self):
        channels = [
            EChannelType.ACCEL_HG_X,
            EChannelType.ACCEL_HG_Y,
            EChannelType.ACCEL_HG_Z,
            EChannelType.MAG_WR_X,
        ]
        samples = [
            [0, 2047, -2048, 0, -32768],
            [64, -1, 1, 42, 32767],
        ]

        content = build_shimmer3r_file(
            channels=channels,
            samples=samples,
            sensors=[ESensorGroup.ACCEL_HG, ESensorGroup.MAG_WR],
        )
        reader = self._open(content)

        # Three high-g channels at two bytes each, one alt mag channel at two bytes,
        # plus the three byte timestamp
        self.assertEqual(
            sum(
                dt.size
                for dt in reader.hardware_revision.get_channel_dtypes(
                    reader.enabled_channels
                )
            ),
            11,
        )

        data, _ = reader.read_data()
        np.testing.assert_equal(data[EChannelType.ACCEL_HG_X], np.array([2047, -1]))
        np.testing.assert_equal(data[EChannelType.ACCEL_HG_Y], np.array([-2048, 1]))
        np.testing.assert_equal(data[EChannelType.ACCEL_HG_Z], np.array([0, 42]))
        np.testing.assert_equal(data[EChannelType.MAG_WR_X], np.array([-32768, 32767]))

    def test_high_g_accel_is_left_aligned_in_the_word(self):
        # A 12 bit value of 1 is transmitted as 0x0010 in big-endian byte order
        content = build_shimmer3r_file(
            channels=[EChannelType.ACCEL_HG_X], samples=[[0, 1]]
        )
        self.assertEqual(content[0x183:0x185], b"\x00\x10")

    def test_alt_triaxcal_params_beyond_the_shimmer3_header(self):
        exp_params = {
            ESensorGroup.ACCEL_HG: (
                np.array([1, 2, 3]),
                np.diag([100, 200, 300]),
                np.array([[0.0, 1.0, 0.0], [-1.0, 0.0, 0.0], [0.0, 0.0, -1.0]]),
            ),
            ESensorGroup.MAG_WR: (
                np.array([-1, -2, -3]),
                np.diag([1711, 1711, 1711]),
                np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]),
            ),
        }

        triaxcal = {}
        for sensor, (offset, gain, alignment) in exp_params.items():
            triaxcal[sensor] = encode_triaxcal_block(
                offset=offset,
                gain=np.diag(gain),
                alignment=(alignment * 100).flatten().astype(int),
            )

        content = build_shimmer3r_file(
            channels=[EChannelType.VBATT], samples=[], triaxcal=triaxcal
        )
        reader = self._open(content)

        for sensor, (exp_offset, exp_gain, exp_alignment) in exp_params.items():
            offset, gain, alignment = reader.get_triaxcal_params(sensor)
            np.testing.assert_almost_equal(offset, exp_offset, decimal=10)
            np.testing.assert_almost_equal(gain, exp_gain, decimal=10)
            np.testing.assert_almost_equal(alignment, exp_alignment, decimal=10)

    def test_has_triaxcal_params(self):
        triaxcal = {
            ESensorGroup.ACCEL_HG: encode_triaxcal_block(
                offset=[1, 2, 3],
                gain=[100, 200, 300],
                alignment=[100, 0, 0, 0, 100, 0, 0, 0, 100],
            ),
            ESensorGroup.MAG_WR: b"\xff" * 21,
        }

        content = build_shimmer3r_file(
            channels=[EChannelType.VBATT], samples=[], triaxcal=triaxcal
        )
        reader = self._open(content)

        self.assertTrue(reader.has_triaxcal_params(ESensorGroup.ACCEL_HG))
        self.assertFalse(reader.has_triaxcal_params(ESensorGroup.MAG_WR))
        # No block was written for the gyroscope, so its block consists of zeros
        self.assertFalse(reader.has_triaxcal_params(ESensorGroup.GYRO))

    def test_gsr_range(self):
        for gsr_range in (0, 1, 2, 3, GSR_RANGE_AUTO):
            with self.subTest(gsr_range=gsr_range):
                content = build_shimmer3r_file(
                    channels=[EChannelType.VBATT], samples=[], gsr_range=gsr_range
                )
                reader = self._open(content)

                self.assertEqual(reader.gsr_range, gsr_range)

    def test_invalid_channel_count_is_rejected(self):
        content = bytearray(
            build_shimmer3r_file(channels=[EChannelType.VBATT], samples=[])
        )

        # A channel list that does not fit into the header
        content[0x13A] = 0xFF
        with self.assertRaises(ValueError):
            self._open(bytes(content))

        # An empty channel list
        content[0x13A] = 0x00
        with self.assertRaises(ValueError):
            self._open(bytes(content))

    def test_unknown_channel_id_is_rejected(self):
        content = bytearray(
            build_shimmer3r_file(channels=[EChannelType.VBATT], samples=[])
        )
        content[0x13B] = 0x7F

        with self.assertRaises(ValueError):
            self._open(bytes(content))

    def test_synchronized_files_are_rejected(self):
        content = build_shimmer3r_file(
            channels=[EChannelType.VBATT], samples=[], sync=True
        )

        with self.assertRaises(NotImplementedError):
            self._open(content)

    def test_global_clock(self):
        content = build_shimmer3r_file(
            channels=[EChannelType.VBATT], samples=[], rtc_diff=0x1234
        )
        reader = self._open(content)

        self.assertEqual(reader.has_global_clock, True)
        self.assertEqual(reader.global_clock_diff, 0x1234)

    def test_exg_registers(self):
        reg1 = b"\x03\xa8\x10\x49\x40\x23\x00\x00\x02\x03"
        reg2 = b"\x03\xa0\x10\xc1\xc1\x00\x00\x00\x02\x01"

        content = build_shimmer3r_file(
            channels=[EChannelType.VBATT], samples=[], exg_reg1=reg1, exg_reg2=reg2
        )
        reader = self._open(content)

        self.assertEqual(reader.exg_reg1.binary, reg1)
        self.assertEqual(reader.exg_reg2.binary, reg2)
