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
from typing import Dict, List, BinaryIO

import numpy as np

from pyshimmer.device import EChannelType, ticks2sec, dr2sr, ExGRegister, get_exg_ch, ChDataTypeAssignment, is_exg_ch
from pyshimmer.reader.binary_reader import ShimmerBinaryReader
from pyshimmer.reader.reader_const import EXG_ADC_REF_VOLT, EXG_ADC_OFFSET
from pyshimmer.util import unwrap


def unwrap_device_timestamps(ts_dev: np.ndarray) -> np.ndarray:
    ts_dtype = ChDataTypeAssignment[EChannelType.TIMESTAMP]
    return unwrap(ts_dev, 2 ** (8 * ts_dtype.size))


def fit_linear_1d(xp, fp, x):
    fit_coef = np.polyfit(xp, fp, 1)
    fn = np.poly1d(fit_coef)
    return fn(x)


class ShimmerReader:

    def __init__(self, fp: BinaryIO = None, bin_reader: ShimmerBinaryReader = None, realign: bool = True,
                 sync: bool = True, post_process: bool = True):
        if fp is not None:
            self._bin_reader = ShimmerBinaryReader(fp)
        elif bin_reader is not None:
            self._bin_reader = bin_reader
        else:
            raise ValueError('Need to provide file object or binary reader as parameter.')

        self._ts = None
        self._ch_samples = {}
        self._realign = realign
        self._sync = sync
        self._pp = post_process

    @staticmethod
    def _apply_synchronization(data_ts: np.ndarray, offset_index: np.ndarray, offsets: np.ndarray):
        # We discard all synchronization offsets for which we do not possess timestamps.
        index_safe = offset_index[offset_index < len(data_ts)]

        offsets_ts = data_ts[index_safe]
        data_offsets = fit_linear_1d(offsets_ts, offsets, data_ts)

        aligned_ts = data_ts - data_offsets
        return aligned_ts

    def _apply_clock_offsets(self, ts: np.ndarray):
        # First, we need calculate absolute timestamps relative to the boot-up time of the Shimmer.
        # In order to do so, we use the 40bit initial timestamp to calculate an offset to apply to
        # each timestamp.
        boot_offset = self._bin_reader.start_timestamp - ts[0]
        ts_boot = ts + boot_offset

        if self._bin_reader.has_global_clock:
            return ts_boot + self._bin_reader.global_clock_diff
        else:
            return ts_boot

    def _is_spaced_equally(self, ts_dev: np.ndarray):
        ts_diff = np.diff(ts_dev)
        return np.all(ts_diff == self._bin_reader.sample_rate)

    def _realign_samples(self, ts: np.ndarray, samples: Dict[EChannelType, np.ndarray]):
        n = len(ts)
        offset = ts[0]

        ts_aligned = offset + np.arange(n) / self.sample_rate

        samples_aligned = {}
        for ch in samples.keys():
            samples_aligned[ch] = np.interp(ts_aligned, ts, samples[ch])

        return ts_aligned, samples_aligned

    def _process_exg_signal(self, ch_type: EChannelType, y: np.ndarray) -> np.ndarray:
        chip_id, ch_id = get_exg_ch(ch_type)
        exg_reg = self.get_exg_reg(chip_id)
        gain = exg_reg.get_ch_gain(ch_id)

        ch_dtype = ChDataTypeAssignment[ch_type]
        resolution = 8 * ch_dtype.size
        sensitivity = EXG_ADC_REF_VOLT / (2 ** (resolution - 1) - 1)

        # According to formula in Shimmer ECG User Guide
        y_volt = (y - EXG_ADC_OFFSET) * sensitivity / gain
        return y_volt

    def _process_signals(self, channels: Dict[EChannelType, np.ndarray]) -> Dict[EChannelType, np.ndarray]:
        result = {}
        for ch, y in channels.items():
            if is_exg_ch(ch):
                result[ch] = self._process_exg_signal(ch, y)
            elif ch == EChannelType.INTERNAL_ADC_13:
                # Adjust the signal unit from mV to V
                result[ch] = y / 1000.0
            else:
                result[ch] = y

        return result

    def load_file_data(self):
        samples, sync_offsets = self._bin_reader.read_data()
        ts_raw = samples.pop(EChannelType.TIMESTAMP)

        ts_unwrapped = unwrap_device_timestamps(ts_raw)
        ts_sane = self._apply_clock_offsets(ts_unwrapped)

        if self._sync and self._bin_reader.has_sync:
            ts_sane = self._apply_synchronization(ts_sane, *sync_offsets)

        if self._pp:
            samples = self._process_signals(samples)

        ts_unaligned = ticks2sec(ts_sane)
        if self._realign and not self._is_spaced_equally(ts_sane):
            self._ts, self._ch_samples = self._realign_samples(ts_unaligned, samples)
        else:
            self._ts, self._ch_samples = ts_unaligned, samples

    def get_exg_reg(self, chip_id: int) -> ExGRegister:
        return ExGRegister(self._bin_reader.get_exg_reg(chip_id))

    def __getitem__(self, item: EChannelType) -> np.ndarray:
        if item == EChannelType.TIMESTAMP:
            return self.timestamp

        return self._ch_samples[item]

    @property
    def timestamp(self) -> np.ndarray:
        return self._ts

    @property
    def channels(self) -> List[EChannelType]:
        # We return all but the first channel which are the timestamps
        return self._bin_reader.enabled_channels[1:]

    @property
    def sample_rate(self) -> float:
        return dr2sr(self._bin_reader.sample_rate)

    @property
    def exg_reg1(self) -> ExGRegister:
        return self.get_exg_reg(0)

    @property
    def exg_reg2(self) -> ExGRegister:
        return self.get_exg_reg(1)
