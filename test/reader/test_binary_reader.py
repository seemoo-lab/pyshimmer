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
from unittest import TestCase

import numpy as np

from pyshimmer.dev.channels import ESensorGroup, get_ch_dtypes
from pyshimmer import EChannelType, ExGRegister
from pyshimmer.reader.shimmer_reader import ShimmerBinaryReader
from .reader_test_util import get_binary_sample_fpath, get_synced_bin_vs_consensys_pair_fpath, get_ecg_sample, \
    get_triaxcal_sample


class ShimmerReaderTest(TestCase):

    def test_parsing_wo_sync(self):
        fpath = get_binary_sample_fpath()
        with open(fpath, 'rb') as f:
            reader = ShimmerBinaryReader(f)

            exp_dr = 65
            exp_sensors = [ESensorGroup.ACCEL_LN, ESensorGroup.BATTERY, ESensorGroup.CH_A13]
            exp_channels = [EChannelType.TIMESTAMP, EChannelType.ACCEL_LN_X, EChannelType.ACCEL_LN_Y,
                            EChannelType.ACCEL_LN_Z, EChannelType.VBATT, EChannelType.INTERNAL_ADC_13]

            sample_size = sum([dt.size for dt in get_ch_dtypes(exp_channels)])
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
            self.assertEqual(reader.exg_reg1.binary, b'\x00\x80\x10\x00\x00\x00\x00\x00\x02\x01')
            self.assertEqual(reader.exg_reg2.binary, b'\x00\x80\x10\x00\x00\x00\x00\x00\x02\x01')

            data, _ = reader.read_data()
            ts = data[EChannelType.TIMESTAMP]

            # Sanity check on the timestamps: they should all be spaced equally apart with a stride that is equal
            # to the sampling rate.
            ts_diff = np.diff(ts)
            correct_diff = np.sum(ts_diff == exp_dr)
            self.assertTrue(correct_diff / len(ts_diff) > 0.98)

    def test_parsing_w_sync(self):
        fpath, _ = get_synced_bin_vs_consensys_pair_fpath()
        with open(fpath, 'rb') as f:
            reader = ShimmerBinaryReader(f)

            exp_dr = 64
            exp_sensors = [ESensorGroup.CH_A13]
            exp_channels = [EChannelType.TIMESTAMP, EChannelType.INTERNAL_ADC_13]
            exp_offsets = np.array([372, 362, 364, 351])
            exp_sync_ts = np.array([3725366, 4071094, 4397558, 4724022])
            exp_exg_reg1 = ExGRegister(b'\x00\x80\x10\x00\x00\x00\x00\x00\x02\x01')
            exp_exg_reg2 = ExGRegister(b'\x00\x80\x10\x00\x00\x00\x00\x00\x02\x01')

            sample_size = sum([dt.size for dt in get_ch_dtypes(exp_channels)])
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

            # Sanity check on the timestamps: they should all be spaced equally apart with a stride that is equal
            # to the sampling rate.
            ts = samples[EChannelType.TIMESTAMP]
            ts_diff = np.diff(ts)
            correct_diff = np.sum(ts_diff == exp_dr)
            self.assertTrue(correct_diff / len(ts_diff) > 0.98)

    def test_ecg_registers(self):
        fpath, _, _ = get_ecg_sample()
        with open(fpath, 'rb') as f:
            reader = ShimmerBinaryReader(f)
            self.assertEqual(reader.exg_reg1.binary, b'\x03\xA8\x10\x49\x40\x23\x00\x00\x02\x03')
            self.assertEqual(reader.exg_reg2.binary, b'\x03\xA0\x10\xC1\xC1\x00\x00\x00\x02\x01')

    # noinspection PyMethodMayBeStatic
    def test_accel_ln_calib_data(self):
        exp_params = {
            ESensorGroup.ACCEL_LN: (
                np.array([2045, 2071, 2033]),
                np.diag([83, 83, 83]),
                np.array([[0.0, 1.0, 0.0],
                          [1.0, 0.0, 0.02],
                          [0.02, -0.01, -1.0]]),
            ),
            ESensorGroup.GYRO: (
                np.array([-123, -29, -35]),
                np.diag([56.68, 57.91, 59.21]),
                np.array([[0.0, 1.0, -0.02],
                          [1.0, 0.0, 0.03],
                          [-0.25, 0.01, -0.97]])
            )
        }

        fpath, _, _ = get_triaxcal_sample()
        with open(fpath, 'rb') as f:
            reader = ShimmerBinaryReader(f)

            for sensor, (exp_offset, exp_gain, exp_alignment) in exp_params.items():
                offset, gain, alignment = reader.get_triaxcal_params(sensor)
                np.testing.assert_almost_equal(offset, exp_offset, decimal=10)
                np.testing.assert_almost_equal(gain, exp_gain, decimal=10)
                np.testing.assert_almost_equal(alignment, exp_alignment, decimal=10)
