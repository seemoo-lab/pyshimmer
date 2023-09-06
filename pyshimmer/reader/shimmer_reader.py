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

from abc import ABC, abstractmethod
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
from typing import Dict, List, BinaryIO

import numpy as np

from pyshimmer.dev.base import ticks2sec, dr2sr
from pyshimmer.dev.channels import ChDataTypeAssignment, get_enabled_channels, EChannelType
from pyshimmer.dev.exg import is_exg_ch, get_exg_ch, ExGRegister
from pyshimmer.reader.binary_reader import ShimmerBinaryReader
from pyshimmer.reader.reader_const import EXG_ADC_REF_VOLT, EXG_ADC_OFFSET, TRIAXCAL_SENSORS
from pyshimmer.util import unwrap


def unwrap_device_timestamps(ts_dev: np.ndarray) -> np.ndarray:
    ts_dtype = ChDataTypeAssignment[EChannelType.TIMESTAMP]
    return unwrap(ts_dev, 2 ** (8 * ts_dtype.size))


def fit_linear_1d(xp, fp, x):
    fit_coef = np.polyfit(xp, fp, 1)
    fn = np.poly1d(fit_coef)
    return fn(x)


class ChannelPostProcessor(ABC):

    @abstractmethod
    def process(self, channels: Dict[EChannelType, np.ndarray], reader: ShimmerBinaryReader) -> \
            Dict[EChannelType, np.ndarray]:
        pass


class SingleChannelProcessor(ChannelPostProcessor, ABC):

    def __init__(self, ch_types: List[EChannelType] = None):
        super().__init__()
        self._ch_types = ch_types

    def process(self, channels: Dict[EChannelType, np.ndarray], reader: ShimmerBinaryReader) -> \
            Dict[EChannelType, np.ndarray]:

        if self._ch_types is None:
            ch_types = list(channels.keys())
        else:
            ch_types = [t for t in self._ch_types if t in channels]

        result = channels.copy()
        for ch_type in ch_types:
            result[ch_type] = self.process_channel(ch_type, channels[ch_type], reader)

        return result

    @abstractmethod
    def process_channel(self, ch_type: EChannelType, y: np.ndarray, reader: ShimmerBinaryReader) -> np.ndarray:
        pass


class ExGProcessor(SingleChannelProcessor):

    def __init__(self):
        exg_channels = [t for t in EChannelType if is_exg_ch(t)]
        super().__init__(exg_channels)

    def process_channel(self, ch_type: EChannelType, y: np.ndarray, reader: ShimmerBinaryReader) -> np.ndarray:
        chip_id, ch_id = get_exg_ch(ch_type)
        exg_reg = reader.get_exg_reg(chip_id)
        gain = exg_reg.get_ch_gain(ch_id)

        ch_dtype = ChDataTypeAssignment[ch_type]
        resolution = 8 * ch_dtype.size
        sensitivity = EXG_ADC_REF_VOLT / (2 ** (resolution - 1) - 1)

        # According to formula in Shimmer ECG User Guide
        y_volt = (y - EXG_ADC_OFFSET) * sensitivity / gain
        return y_volt


class PPGProcessor(SingleChannelProcessor):

    def __init__(self):
        super().__init__([EChannelType.INTERNAL_ADC_13])

    def process_channel(self, ch_type: EChannelType, y: np.ndarray, reader: ShimmerBinaryReader) -> np.ndarray:
        # Convert from mV to V
        return y / 1000.0


class TriAxCalProcessor(ChannelPostProcessor):

    def process(self, channels: Dict[EChannelType, np.ndarray], reader: ShimmerBinaryReader) -> \
            Dict[EChannelType, np.ndarray]:
        result = channels.copy()

        active_sensors = [s for s in reader.enabled_sensors if s in TRIAXCAL_SENSORS]
        for sensor in active_sensors:
            sensor_channels = get_enabled_channels([sensor])
            channel_data = np.stack([channels[c] for c in sensor_channels])
            o, g, a = reader.get_triaxcal_params(sensor)

            g_a = np.matmul(g, a)
            r = np.linalg.solve(g_a, channel_data - o[..., None])

            for i, ch in enumerate(sensor_channels):
                result[ch] = r[i]

        return result


class ShimmerReader:

    def __init__(self, fp: BinaryIO = None, bin_reader: ShimmerBinaryReader = None,
                 sync: bool = True, post_process: bool = True, processors: List[ChannelPostProcessor] = None):
        if fp is not None:
            self._bin_reader = ShimmerBinaryReader(fp)
        elif bin_reader is not None:
            self._bin_reader = bin_reader
        else:
            raise ValueError('Need to provide file object or binary reader as parameter.')

        self._ts = None
        self._ch_samples = {}
        self._sync = sync

        self._pp = post_process
        if processors is not None:
            self._processors = processors
        else:
            self._processors = [
                ExGProcessor(),
                PPGProcessor(),
                TriAxCalProcessor(),
            ]

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

    def _process_signals(self, channels: Dict[EChannelType, np.ndarray]) -> Dict[EChannelType, np.ndarray]:
        result = channels.copy()

        for processor in self._processors:
            result = processor.process(result, self._bin_reader)

        return result

    def load_file_data(self):
        samples, sync_offsets = self._bin_reader.read_data()
        ts_raw = samples.pop(EChannelType.TIMESTAMP)

        ts_unwrapped = unwrap_device_timestamps(ts_raw)
        ts_sane = self._apply_clock_offsets(ts_unwrapped)

        if self._sync and self._bin_reader.has_sync:
            ts_sane = self._apply_synchronization(ts_sane, *sync_offsets)

        if self._pp:
            self._ch_samples = self._process_signals(samples)
        else:
            self._ch_samples = samples

        self._ts = ticks2sec(ts_sane)

    def get_exg_reg(self, chip_id: int) -> ExGRegister:
        return self._bin_reader.get_exg_reg(chip_id)

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
