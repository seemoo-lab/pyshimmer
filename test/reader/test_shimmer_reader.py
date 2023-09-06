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

from typing import List, Set
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
from unittest import TestCase
from unittest.mock import Mock, PropertyMock

import numpy as np
import pandas as pd

from pyshimmer import EChannelType, ExGRegister
from pyshimmer.dev.base import ticks2sec
from pyshimmer.dev.channels import ESensorGroup, get_enabled_channels
from pyshimmer.dev.exg import get_exg_ch
from pyshimmer.reader.binary_reader import ShimmerBinaryReader
from pyshimmer.reader.shimmer_reader import ShimmerReader, SingleChannelProcessor, PPGProcessor, TriAxCalProcessor
from .reader_test_util import get_bin_vs_consensys_pair_fpath, get_synced_bin_vs_consensys_pair_fpath, get_ecg_sample, \
    get_triaxcal_sample


class ShimmerReaderTest(TestCase):

    def test_reader_timestep_interpolation(self):
        sr = 5
        ts_dev = np.array([0, 5, 10, 15, 21, 25, 29, 35])
        ts = ticks2sec(ts_dev)
        vbatt = np.array([93, 85, 78, 74, 71, 68, 65, 64])
        samples = {
            EChannelType.TIMESTAMP: ts_dev,
            EChannelType.VBATT: vbatt,
        }

        m_br = Mock(spec=ShimmerBinaryReader)
        m_br.read_data.return_value = (samples, [])
        type(m_br).sample_rate = PropertyMock(return_value=sr)
        type(m_br).enabled_sensors = PropertyMock(return_value=[])
        type(m_br).has_sync = PropertyMock(return_value=False)
        type(m_br).has_global_clock = PropertyMock(return_value=False)
        type(m_br).start_timestamp = PropertyMock(return_value=0)

        reader = ShimmerReader(bin_reader=m_br)
        reader.load_file_data()

        ts_aligned = reader.timestamp
        self.assertEqual(len(ts_aligned), len(ts))

        vbatt_aligned = reader[EChannelType.VBATT]
        np.testing.assert_equal(vbatt[ts_aligned == ts], vbatt_aligned[ts_aligned == ts])

    def test_timestamp_unwrapping(self):
        sr = 65
        ts_dev = np.arange(0, 4 * (2 ** 24), sr)
        ts_dev_wrapped = ts_dev % 2 ** 24

        ts = ticks2sec(ts_dev)
        vbatt = np.random.randint(0, 100 + 1, len(ts_dev))

        m_br = Mock(spec=ShimmerBinaryReader)
        type(m_br).has_sync = PropertyMock(return_value=False)
        type(m_br).enabled_sensors = PropertyMock(return_value=[])
        type(m_br).sample_rate = PropertyMock(return_value=sr)
        type(m_br).has_global_clock = PropertyMock(return_value=False)
        type(m_br).start_timestamp = PropertyMock(return_value=0)

        samples = {
            EChannelType.VBATT: vbatt,
            EChannelType.TIMESTAMP: ts_dev_wrapped,
        }
        m_br.read_data.return_value = (samples, [])

        reader = ShimmerReader(bin_reader=m_br)
        reader.load_file_data()

        ts_actual = reader.timestamp
        self.assertEqual(len(ts_actual), len(ts))
        np.testing.assert_almost_equal(ts_actual, ts)
        np.testing.assert_equal(reader[EChannelType.VBATT], vbatt)
        np.testing.assert_equal(reader.timestamp, reader[EChannelType.TIMESTAMP])

    def test_timestamp_synchronization(self):
        sr = 5
        ts = np.array([0, 5, 10, 15, 20, 25, 30, 35, 40, 45])
        vbatt = np.array([93, 85, 78, 74, 71, 68, 65, 64, 10, 24])
        samples = {
            EChannelType.TIMESTAMP: ts,
            EChannelType.VBATT: vbatt,
        }

        sync_index = np.array([0, len(ts) - 1])
        sync_offset = np.array([1, 0])

        m_br = Mock(spec=ShimmerBinaryReader)
        m_br.read_data.return_value = (samples, [sync_index, sync_offset])
        type(m_br).sample_rate = PropertyMock(return_value=sr)
        type(m_br).enabled_sensors = PropertyMock(return_value=[])
        type(m_br).has_sync = PropertyMock(return_value=True)
        type(m_br).has_global_clock = PropertyMock(return_value=False)
        type(m_br).start_timestamp = PropertyMock(return_value=0)

        reader = ShimmerReader(bin_reader=m_br)
        reader.load_file_data()

        ts_sync_dev = ts - np.linspace(1, 0, len(ts))
        exp_ts = ticks2sec(ts_sync_dev)
        act_ts = reader.timestamp

        self.assertEqual(len(exp_ts), len(act_ts))
        np.testing.assert_almost_equal(act_ts, exp_ts)
        np.testing.assert_equal(vbatt, reader[EChannelType.VBATT])

    # noinspection PyMethodMayBeStatic
    def test_compare_ppg_processiong_to_consensys(self):
        raw_file, csv_file = get_bin_vs_consensys_pair_fpath()

        exp_sr = 504.12
        exp_channels = [EChannelType.ACCEL_LN_X, EChannelType.ACCEL_LN_Y, EChannelType.ACCEL_LN_Z, EChannelType.VBATT,
                        EChannelType.INTERNAL_ADC_13]

        with open(raw_file, 'rb') as f:
            reader = ShimmerReader(f)
            reader.load_file_data()

        self.assertEqual(exp_channels, reader.channels)
        self.assertAlmostEqual(exp_sr, reader.sample_rate, 2)

        r = np.loadtxt(csv_file, delimiter='\t', skiprows=3, usecols=(0, 1))
        expected_ts = r[:, 0]
        expected_ppg = r[:, 1]

        actual_ts = reader.timestamp * 1000  # needs to be in ms
        actual_ppg = reader[EChannelType.INTERNAL_ADC_13] * 1000.0  # needs to be in mV

        np.testing.assert_almost_equal(actual_ts.flatten(), expected_ts.flatten())
        np.testing.assert_almost_equal(actual_ppg, expected_ppg)

    def test_compare_sync_processing_to_consensys(self):
        bin_path, csv_path = get_synced_bin_vs_consensys_pair_fpath()

        exp_sr = 512.0
        exp_channels = [EChannelType.INTERNAL_ADC_13]

        with open(bin_path, 'rb') as f:
            reader = ShimmerReader(f, sync=True)
            reader.load_file_data()

        csv_data = np.loadtxt(csv_path, delimiter='\t', skiprows=3, usecols=(0, 1))
        expected_ts = csv_data[:, 0]
        expected_ppg = csv_data[:, 1]

        actual_ts = reader.timestamp * 1000
        actual_ppg = reader[EChannelType.INTERNAL_ADC_13] * 1000.0  # needs to be in mV

        self.assertEqual(exp_channels, reader.channels)
        self.assertEqual(exp_sr, reader.sample_rate)
        np.testing.assert_almost_equal(actual_ts.flatten(), expected_ts.flatten())
        np.testing.assert_almost_equal(actual_ppg.flatten(), expected_ppg.flatten())

    def test_reader_exg_register(self):
        exp_reg1_content = bytes(range(10))
        exp_reg1 = ExGRegister(exp_reg1_content)
        exp_reg2_content = bytes(range(10, 0, -1))
        exp_reg2 = ExGRegister(exp_reg2_content)
        exp_regs = [exp_reg1, exp_reg2]

        m_br = Mock(spec=ShimmerBinaryReader)
        m_br.get_exg_reg.side_effect = lambda x: exp_regs[x]
        type(m_br).exg_reg1 = PropertyMock(return_value=exp_reg1)
        type(m_br).exg_reg2 = PropertyMock(return_value=exp_reg2)
        reader = ShimmerReader(bin_reader=m_br)

        for i in range(2):
            self.assertEqual(reader.get_exg_reg(i), exp_regs[i])

        actual_reg1 = reader.exg_reg1
        actual_reg2 = reader.exg_reg2
        self.assertEqual(actual_reg1, exp_reg1)
        self.assertEqual(actual_reg2, exp_reg2)

    # noinspection PyMethodMayBeStatic
    def test_post_process_exg_signal(self):
        exg_reg1 = ExGRegister(b'\x03\x80\x10\x40\x40\x00\x00\x00\x02\x01')
        exg1_gain = 4
        exg_reg2 = ExGRegister(b'\x03\x80\x10\x20\x20\x00\x00\x00\x02\x01')
        exg2_gain = 2

        chip_gain = {
            0: exg1_gain,
            1: exg2_gain,
        }

        samples = {
            EChannelType.EXG_ADS1292R_1_CH1_24BIT: np.random.randn(1000),
            EChannelType.EXG_ADS1292R_2_CH2_24BIT: np.random.randn(1000),
            EChannelType.EXG_ADS1292R_1_CH1_16BIT: np.random.randn(1000),
            EChannelType.EXG_ADS1292R_2_CH2_16BIT: np.random.randn(1000),
        }

        samples_w_ts = {**samples, EChannelType.TIMESTAMP: np.arange(1000)}

        m_br = Mock(spec=ShimmerBinaryReader)
        m_br.get_exg_reg.side_effect = lambda x: exg_reg1 if x == 0 else exg_reg2
        m_br.read_data.side_effect = lambda: (dict(samples_w_ts), ((), ()))
        type(m_br).sample_rate = PropertyMock(return_value=1)
        type(m_br).enabled_sensors = PropertyMock(return_value=[])
        type(m_br).has_sync = PropertyMock(return_value=False)
        type(m_br).has_global_clock = PropertyMock(return_value=False)
        type(m_br).start_timestamp = PropertyMock(return_value=0)
        type(m_br).exg_reg1 = PropertyMock(return_value=exg_reg1)
        type(m_br).exg_reg2 = PropertyMock(return_value=exg_reg2)

        reader = ShimmerReader(bin_reader=m_br, post_process=False)
        reader.load_file_data()
        for ch_type in samples:
            np.testing.assert_equal(samples[ch_type], reader[ch_type])

        reader = ShimmerReader(bin_reader=m_br, post_process=True)
        reader.load_file_data()

        for ch in samples:
            bit = 16 if '16' in ch.name else 24
            gain = chip_gain[get_exg_ch(ch)[0]]
            expected = (samples[ch] - 0) * 2.420 / (2 ** (bit - 1) - 1) / gain
            actual = reader[ch]
            np.testing.assert_almost_equal(actual, expected)

    # noinspection PyMethodMayBeStatic
    def test_compare_exg_processing_to_consensys(self):
        bin_path, uncal_path, cal_path = get_ecg_sample()

        def verify(bin_file_path, expected, post_process):
            with open(bin_file_path, 'rb') as f:
                reader = ShimmerReader(f, post_process=post_process, sync=False)
                reader.load_file_data()

            actual = reader[EChannelType.EXG_ADS1292R_1_CH1_24BIT]
            np.testing.assert_almost_equal(actual, expected[1])

            actual = reader[EChannelType.EXG_ADS1292R_1_CH2_24BIT]
            np.testing.assert_almost_equal(actual, expected[2])

        expected_uncal = np.loadtxt(uncal_path, delimiter='\t', skiprows=3, usecols=(0, 1, 2)).T
        expected_cal = np.loadtxt(cal_path, delimiter='\t', skiprows=3, usecols=(0, 1, 2)).T / 1000.0  # Volt

        verify(bin_path, expected_uncal, post_process=False)
        verify(bin_path, expected_cal, post_process=True)

    # noinspection PyMethodMayBeStatic
    def test_compare_triaxcal_to_consensys(self):
        bin_path, uncal_path, cal_path = get_triaxcal_sample()

        consensys_csv = pd.read_csv(cal_path, sep=",", skiprows=(0, 2), usecols=list(range(14)))
        col_mapping = {
            EChannelType.ACCEL_LN_X: "Shimmer_952D_Accel_LN_X_CAL",
            EChannelType.ACCEL_LN_Y: "Shimmer_952D_Accel_LN_Y_CAL",
            EChannelType.ACCEL_LN_Z: "Shimmer_952D_Accel_LN_Z_CAL",
            EChannelType.ACCEL_LSM303DLHC_X: "Shimmer_952D_Accel_WR_X_CAL",
            EChannelType.ACCEL_LSM303DLHC_Y: "Shimmer_952D_Accel_WR_Y_CAL",
            EChannelType.ACCEL_LSM303DLHC_Z: "Shimmer_952D_Accel_WR_Z_CAL",
            EChannelType.GYRO_MPU9150_X: "Shimmer_952D_Gyro_X_CAL",
            EChannelType.GYRO_MPU9150_Y: "Shimmer_952D_Gyro_Y_CAL",
            EChannelType.GYRO_MPU9150_Z: "Shimmer_952D_Gyro_Z_CAL",
            EChannelType.MAG_LSM303DLHC_X: "Shimmer_952D_Mag_X_CAL",
            EChannelType.MAG_LSM303DLHC_Y: "Shimmer_952D_Mag_Y_CAL",
            EChannelType.MAG_LSM303DLHC_Z: "Shimmer_952D_Mag_Z_CAL",
        }

        with open(bin_path, 'rb') as f:
            reader = ShimmerReader(f)
            reader.load_file_data()

            for rdr_col, csv_col in col_mapping.items():
                rdr_channel = reader[rdr_col]
                csv_channel = consensys_csv[csv_col]
                np.testing.assert_almost_equal(rdr_channel, csv_channel.to_numpy())


class SignalPostProcessorTest(TestCase):

    # noinspection PyTypeChecker
    def test_single_channel_processor(self):
        class TestProcessor(SingleChannelProcessor):

            def __init__(self, channels: List[EChannelType] = None):
                super().__init__(channels)

                self._seen = []

            def process_channel(self, ch_type: EChannelType, y: np.ndarray, reader: ShimmerBinaryReader) -> np.ndarray:
                self._seen.append(ch_type)
                return y

            @property
            def seen(self) -> Set[EChannelType]:
                return set(self._seen)

        ch_data = {
            EChannelType.TIMESTAMP: np.random.randn(10),
            EChannelType.VBATT: np.random.randn(10),
            EChannelType.INTERNAL_ADC_13: np.random.randn(10),
            EChannelType.ACCEL_LN_X: np.random.randn(10),
        }
        ch_types = set(ch_data.keys())

        proc = TestProcessor()
        proc.process(ch_data, None)
        self.assertEqual(proc.seen, ch_types)

        proc = TestProcessor([EChannelType.VBATT])
        proc.process(ch_data, None)
        self.assertEqual(proc.seen, {EChannelType.VBATT})

        proc = TestProcessor([EChannelType.VBATT, EChannelType.ACCEL_LN_Y])
        proc.process(ch_data, None)
        self.assertEqual(proc.seen, {EChannelType.VBATT})

        proc = TestProcessor([EChannelType.VBATT, EChannelType.ACCEL_LN_X])
        proc.process(ch_data, None)
        self.assertEqual(proc.seen, {EChannelType.VBATT, EChannelType.ACCEL_LN_X})

    # noinspection PyMethodMayBeStatic
    def test_ppg_processor(self):
        ppg_data = np.random.randn(10)
        ch_data = {
            EChannelType.TIMESTAMP: np.random.randn(10),
            EChannelType.VBATT: np.random.randn(10),
            EChannelType.INTERNAL_ADC_13: ppg_data,
            EChannelType.ACCEL_LN_X: np.random.randn(10),
        }

        proc = PPGProcessor()
        # noinspection PyTypeChecker
        output = proc.process(ch_data, None)

        for ch, y in output.items():
            if ch != EChannelType.INTERNAL_ADC_13:
                np.testing.assert_equal(y, ch_data[ch])
            else:
                np.testing.assert_equal(y, ppg_data / 1000.0)

    # noinspection PyMethodMayBeStatic
    def test_triaxcal_processor(self):
        o, g, a = np.array([1, 2, 3]), np.diag([4, 5, 6]), np.diag([7, 8, 9])
        params = {ESensorGroup.ACCEL_LN: (o, g, a)}

        ch_types = get_enabled_channels(list(params.keys()))

        data_arr = np.random.randn(3, 100)
        data_dict = {c: data_arr[i] for i, c in enumerate(ch_types)}

        mock_reader = Mock(spec=ShimmerBinaryReader)
        mock_reader.get_triaxcal_params.side_effect = lambda x: params[x]
        type(mock_reader).enabled_sensors = PropertyMock(return_value=list(params.keys()))

        proc = TriAxCalProcessor()
        actual_dict = proc.process(data_dict, mock_reader)
        actual_arr = np.stack([actual_dict[c] for c in ch_types])

        k = np.matmul(np.linalg.inv(a), np.linalg.inv(g))
        exp_arr = np.matmul(k, data_arr - o[..., None])

        np.testing.assert_almost_equal(actual_arr, exp_arr)
