from unittest import TestCase
from unittest.mock import Mock, PropertyMock

import numpy as np

from pyshimmer.device import EChannelType, ticks2sec, get_exg_ch
from pyshimmer.reader.binary_reader import ShimmerBinaryReader
from pyshimmer.reader.shimmer_reader import ShimmerReader
from .reader_test_util import get_bin_vs_consensys_pair_fpath, get_synced_bin_vs_consensys_pair_fpath, get_ecg_sample


class ShimmerReaderTest(TestCase):

    def test_reader_alignment(self):
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
        type(m_br).has_sync = PropertyMock(return_value=False)
        type(m_br).has_global_clock = PropertyMock(return_value=False)
        type(m_br).start_timestamp = PropertyMock(return_value=0)

        reader = ShimmerReader(bin_reader=m_br)
        reader.load_file_data()

        ts_aligned = reader.timestamp
        self.assertEqual(len(ts_aligned), len(ts))

        vbatt_aligned = reader[EChannelType.VBATT]
        np.testing.assert_equal(vbatt[ts_aligned == ts], vbatt_aligned[ts_aligned == ts])

    def test_ts_unwrap(self):
        sr = 65
        ts_dev = np.arange(0, 4 * (2 ** 24), sr)
        ts_dev_wrapped = ts_dev % 2 ** 24

        ts = ticks2sec(ts_dev)
        vbatt = np.random.randint(0, 100 + 1, len(ts_dev))

        m_br = Mock(spec=ShimmerBinaryReader)
        type(m_br).has_sync = PropertyMock(return_value=False)
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

    def test_ts_sync(self):
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
        type(m_br).has_sync = PropertyMock(return_value=True)
        type(m_br).has_global_clock = PropertyMock(return_value=False)
        type(m_br).start_timestamp = PropertyMock(return_value=0)

        reader = ShimmerReader(bin_reader=m_br, realign=False)
        reader.load_file_data()

        ts_sync_dev = ts - np.linspace(1, 0, len(ts))
        exp_ts = ticks2sec(ts_sync_dev)
        act_ts = reader.timestamp

        self.assertEqual(len(exp_ts), len(act_ts))
        np.testing.assert_almost_equal(act_ts, exp_ts)
        np.testing.assert_equal(vbatt, reader[EChannelType.VBATT])

    # noinspection PyMethodMayBeStatic
    def test_consensys_comparison(self):
        raw_file, csv_file = get_bin_vs_consensys_pair_fpath()

        exp_sr = 504.12
        exp_channels = [EChannelType.ACCEL_LN_X, EChannelType.ACCEL_LN_Y, EChannelType.ACCEL_LN_Z, EChannelType.VBATT,
                        EChannelType.INTERNAL_ADC_13]

        with open(raw_file, 'rb') as f:
            reader = ShimmerReader(f, realign=False)
            reader.load_file_data()

        self.assertEqual(exp_channels, reader.channels)
        self.assertAlmostEqual(exp_sr, reader.sample_rate, 2)

        r = np.loadtxt(csv_file, delimiter='\t', skiprows=3, usecols=(0, 1))
        expected_ts = r[:, 0]
        expected_ppg = r[:, 1]

        actual_ts = reader.timestamp * 1000  # needs to be in ms
        actual_ppg = reader[EChannelType.INTERNAL_ADC_13] * 1000.0 # needs to be in mV

        np.testing.assert_almost_equal(actual_ts.flatten(), expected_ts.flatten())
        np.testing.assert_almost_equal(actual_ppg, expected_ppg)

    def test_file_wsync(self):
        bin_path, csv_path = get_synced_bin_vs_consensys_pair_fpath()

        exp_sr = 512.0
        exp_channels = [EChannelType.INTERNAL_ADC_13]

        with open(bin_path, 'rb') as f:
            reader = ShimmerReader(f, realign=False, sync=True)
            reader.load_file_data()

        csv_data = np.loadtxt(csv_path, delimiter='\t', skiprows=3, usecols=(0, 1))
        expected_ts = csv_data[:, 0]
        expected_ppg = csv_data[:, 1]

        actual_ts = reader.timestamp * 1000
        actual_ppg = reader[EChannelType.INTERNAL_ADC_13] * 1000.0 # needs to be in mV

        self.assertEqual(exp_channels, reader.channels)
        self.assertEqual(exp_sr, reader.sample_rate)
        np.testing.assert_almost_equal(actual_ts.flatten(), expected_ts.flatten())
        np.testing.assert_almost_equal(actual_ppg.flatten(), expected_ppg.flatten())

    def test_reader_exg_register(self):
        exp_reg1 = bytes(range(10))
        exp_reg2 = bytes(range(10, 0, -1))
        exp_regs = [exp_reg1, exp_reg2]

        m_br = Mock(spec=ShimmerBinaryReader)
        m_br.get_exg_reg.side_effect = lambda x: exp_regs[x]
        type(m_br).exg_reg1 = PropertyMock(return_value=exp_reg1)
        type(m_br).exg_reg2 = PropertyMock(return_value=exp_reg2)
        reader = ShimmerReader(bin_reader=m_br)

        for i in range(2):
            self.assertEqual(reader.get_exg_reg(i).binary, exp_regs[i])

        actual_reg1 = reader.exg_reg1
        actual_reg2 = reader.exg_reg2
        self.assertEqual(actual_reg1.binary, exp_reg1)
        self.assertEqual(actual_reg2.binary, exp_reg2)

    # noinspection PyMethodMayBeStatic
    def test_post_process_exg_signal(self):
        exg_reg1 = b'\x03\x80\x10\x40\x40\x00\x00\x00\x02\x01'
        exg1_gain = 4
        exg_reg2 = b'\x03\x80\x10\x20\x20\x00\x00\x00\x02\x01'
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
    def test_exg_processing_consensys(self):
        bin_path, uncal_path, cal_path = get_ecg_sample()

        def verify(bin_file_path, expected, post_process):
            with open(bin_file_path, 'rb') as f:
                reader = ShimmerReader(f, post_process=post_process, realign=False, sync=False)
                reader.load_file_data()

            actual = reader[EChannelType.EXG_ADS1292R_1_CH1_24BIT]
            np.testing.assert_almost_equal(actual, expected[1])

            actual = reader[EChannelType.EXG_ADS1292R_1_CH2_24BIT]
            np.testing.assert_almost_equal(actual, expected[2])

        expected_uncal = np.loadtxt(uncal_path, delimiter='\t', skiprows=3, usecols=(0, 1, 2)).T
        expected_cal = np.loadtxt(cal_path, delimiter='\t', skiprows=3, usecols=(0, 1, 2)).T / 1000.0  # Volt

        verify(bin_path, expected_uncal, post_process=False)
        verify(bin_path, expected_cal, post_process=True)
