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
import struct
from typing import List, Tuple, Union, BinaryIO

import numpy as np

from pyshimmer.dev.channels import ESensorGroup, get_ch_dtypes, get_enabled_channels, EChannelType, \
    ENABLED_SENSORS_LEN, deserialize_sensors
from pyshimmer.dev.exg import ExGRegister
from pyshimmer.util import FileIOBase, unpack, bit_is_set
from .reader_const import RTC_CLOCK_DIFF_OFFSET, ENABLED_SENSORS_OFFSET, SR_OFFSET, \
    START_TS_OFFSET, START_TS_LEN, TRIAL_CONFIG_OFFSET, TRIAL_CONFIG_MASTER, TRIAL_CONFIG_SYNC, BLOCK_LEN, \
    DATA_LOG_OFFSET, EXG_REG_OFFSET, EXG_REG_LEN, TRIAXCAL_FILE_OFFSET, TRIAXCAL_OFFSET_SCALING, \
    TRIAXCAL_GAIN_SCALING, TRIAXCAL_ALIGNMENT_SCALING


class ShimmerBinaryReader(FileIOBase):

    def __init__(self, fp: BinaryIO):
        super().__init__(fp)

        self._sensors = []
        self._channels = []
        self._sr = 0
        self._rtc_diff = 0
        self._start_ts = 0
        self._trial_config = 0

        self._read_header()

    @staticmethod
    def get_data_channels(sensors):
        channels = get_enabled_channels(sensors)
        channels_with_ts = [EChannelType.TIMESTAMP] + channels
        return channels_with_ts

    def _read_header(self) -> None:
        self._sr = self._read_sample_rate()
        self._sensors = self._read_enabled_sensors()
        self._channels = self.get_data_channels(self._sensors)
        self._channel_dtypes = get_ch_dtypes(self._channels)
        self._rtc_diff = self._read_rtc_clock_diff()
        self._start_ts = self._read_start_time()
        self._trial_config = self._read_trial_config()
        self._exg_regs = self._read_exg_regs()

        self._samples_per_block, self._block_size = self._calculate_block_size()

    def _read_sample_rate(self) -> int:
        self._seek(SR_OFFSET)
        return self._read_packed('<H')

    def _read_enabled_sensors(self) -> List[ESensorGroup]:
        self._seek(ENABLED_SENSORS_OFFSET)
        sensor_bitfield = self._read(ENABLED_SENSORS_LEN)
        enabled_sensors = deserialize_sensors(sensor_bitfield)

        return enabled_sensors

    def _read_rtc_clock_diff(self) -> int:
        self._seek(RTC_CLOCK_DIFF_OFFSET)
        rtc_diff_ticks = self._read_packed('>Q')
        return rtc_diff_ticks

    def _read_start_time(self) -> int:
        self._seek(START_TS_OFFSET)
        ts_bin = self._read(START_TS_LEN)

        # The timestamp is 5 byte long in little endian byte order, but has its MSB at offset 0 instead of 4.
        # Due to this, we need to move the last byte back to the end, pad it to 8 bytes and parse it as 64bit value.
        ts_bin_flipped = ts_bin[1:] + ts_bin[0:1]
        ts_bin_padded = ts_bin_flipped + b'\x00' * 3

        ts_ticks = struct.unpack('<Q', ts_bin_padded)
        return unpack(ts_ticks)

    def _read_trial_config(self) -> int:
        self._seek(TRIAL_CONFIG_OFFSET)
        return self._read_packed('<H')

    def _calculate_block_size(self):
        sync_stamp = 9 * self.has_sync
        sample_size = sum([d.size for d in self._channel_dtypes])

        num_samples = int((BLOCK_LEN - sync_stamp) / sample_size)
        block_len = num_samples * sample_size + sync_stamp

        return num_samples, block_len

    def _read_sync_offset(self) -> Union[None, int]:
        # For this read operation we assume that every synchronization offset is immediately followed by a
        # timestamp as it is described in the manuals. We need to pair every sync offset with a timestamp for
        # interpolation at a later point in time.
        offset_sign_bool = self._read_packed('B')
        offset_sign = 1 - 2 * offset_sign_bool
        offset_mag = self._read_packed('<Q')

        if offset_mag == 2 ** 64 - 1:
            return None

        offset = offset_sign * offset_mag

        return offset

    def _read_sample(self) -> List:
        ch_values = []

        for ch, dtype in zip(self._channels, self._channel_dtypes):
            val_bin = self._read(dtype.size)
            ch_values.append(dtype.decode(val_bin))

        return ch_values

    def _read_data_block(self) -> Tuple[List[List], int]:
        sync_tuple = None
        samples = []

        try:
            if self.has_sync:
                sync_tuple = self._read_sync_offset()

            for i in range(self._samples_per_block):
                sample = self._read_sample()
                samples += [sample]
        except IOError:
            pass

        return samples, sync_tuple

    def _read_contents(self) -> Tuple[List, List[Tuple[int, int]]]:
        sync_offsets = []
        samples = []
        sample_ctr = 0

        self._seek(DATA_LOG_OFFSET)
        while True:
            block_samples, sync_offset = self._read_data_block()

            if sync_offset is not None:
                sync_offsets += [(sample_ctr, sync_offset)]

            samples += block_samples
            sample_ctr += len(block_samples)

            if len(block_samples) < self.samples_per_block:
                # We have reached EOF
                break

        return samples, sync_offsets

    def _read_exg_regs(self) -> Tuple[bytes, bytes]:
        self._seek(EXG_REG_OFFSET)

        reg1 = self._read(EXG_REG_LEN)
        reg2 = self._read(EXG_REG_LEN)
        return reg1, reg2

    def _read_triaxcal_params(self, offset: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        fmt = ">" + 6 * 'h' + 9 * 'b'

        self._seek(offset)
        calib_param_bytes = self._read(struct.calcsize(fmt))
        params_raw = struct.unpack(fmt, calib_param_bytes)

        offset = np.array(params_raw[:3])
        gain = np.diag(params_raw[3:6])
        alignment = np.array(params_raw[6:]).reshape((3, 3))

        return offset, gain, alignment

    def read_data(self):
        samples, sync_offsets = self._read_contents()

        samples_per_ch = list(zip(*samples))
        arr_per_ch = [np.array(s) for s in samples_per_ch]
        samples_dict = dict(zip(self._channels, arr_per_ch))

        if self.has_sync and len(sync_offsets) > 0:
            off_index, offset = list(zip(*sync_offsets))
            off_index_arr = np.array(off_index)
            offset_arr = np.array(offset)
            sync_data = (off_index_arr, offset_arr)
        else:
            sync_data = ((), ())

        return samples_dict, sync_data

    def get_exg_reg(self, chip_id: int) -> ExGRegister:
        reg_content = self._exg_regs[chip_id]
        return ExGRegister(reg_content)

    def get_triaxcal_params(self, sensor: ESensorGroup) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        offset = TRIAXCAL_FILE_OFFSET[sensor]
        sc_offset = TRIAXCAL_OFFSET_SCALING[sensor]
        sc_gain = TRIAXCAL_GAIN_SCALING[sensor]
        sc_alignment = TRIAXCAL_ALIGNMENT_SCALING[sensor]

        offset, gain, alignment = self._read_triaxcal_params(offset)
        return offset * sc_offset, gain * sc_gain, alignment * sc_alignment

    @property
    def sample_rate(self) -> int:
        return self._sr

    @property
    def block_size(self) -> int:
        return self._block_size

    @property
    def samples_per_block(self) -> int:
        return self._samples_per_block

    @property
    def enabled_sensors(self) -> List[ESensorGroup]:
        return self._sensors

    @property
    def enabled_channels(self) -> List[EChannelType]:
        return self._channels

    @property
    def has_global_clock(self) -> bool:
        return self._rtc_diff != 0x0

    @property
    def global_clock_diff(self) -> int:
        return self._rtc_diff

    @property
    def start_timestamp(self) -> int:
        return self._start_ts

    @property
    def has_sync(self) -> bool:
        return bit_is_set(self._trial_config, TRIAL_CONFIG_SYNC)

    @property
    def is_sync_master(self) -> bool:
        return bit_is_set(self._trial_config, TRIAL_CONFIG_MASTER)

    @property
    def exg_reg1(self) -> ExGRegister:
        return self.get_exg_reg(0)

    @property
    def exg_reg2(self) -> ExGRegister:
        return self.get_exg_reg(1)
