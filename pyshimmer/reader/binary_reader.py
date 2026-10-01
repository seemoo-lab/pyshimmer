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

import struct
from typing import BinaryIO

import numpy as np

from pyshimmer.dev.base import ExpansionBoard
from pyshimmer.dev.calibration import has_calib_params
from pyshimmer.dev.channels import (
    ESensorGroup,
    EChannelType,
)
from pyshimmer.dev.exg import ExGRegister
from pyshimmer.dev.fw_version import FirmwareType, FirmwareVersion
from pyshimmer.dev.pressure import (
    BMP180Calibration,
    BMP280Calibration,
    BMP390Calibration,
    BMP581Calibration,
    EPressureSensor,
    PressureCalibration,
)
from pyshimmer.dev.revisions import RevisionRegistry, HardwareVersion, HardwareRevision
from pyshimmer.util import FileIOBase, unpack, bit_is_set
from .reader_const import (
    RTC_CLOCK_DIFF_OFFSET,
    ENABLED_SENSORS_OFFSET,
    SR_OFFSET,
    START_TS_OFFSET,
    START_TS_LEN,
    TRIAL_CONFIG_OFFSET,
    TRIAL_CONFIG_MASTER,
    TRIAL_CONFIG_SYNC,
    BLOCK_LEN,
    HW_VERSION_OFFSET,
    FW_TYPE_OFFSET,
    FW_VERSION_OFFSET,
    EXP_BOARD_OFFSET,
    EXP_BOARD_LEN,
    PRESSURE_RESOLUTION_OFFSET,
    EXG_REG_OFFSET,
    EXG_REG_LEN,
    TRIAXCAL_FMT,
)


class ShimmerBinaryReader(FileIOBase):

    def __init__(self, fp: BinaryIO, hw_version: HardwareVersion = None):
        """Read the contents of a binary file recorded by a Shimmer device

        :param fp: The binary file to read
        :param hw_version: The hardware version of the device that recorded the file.
            If None, the version is read from the file header. Provide it explicitly
            only for files whose header does not carry a usable version field.
        """
        super().__init__(fp)

        self._sensors = []
        self._channels = []
        self._sr = 0
        self._rtc_diff = 0
        self._start_ts = 0
        self._trial_config = 0
        self._pressure_calib = None

        if hw_version is None:
            hw_version = self._read_hardware_version()
        self._revision = RevisionRegistry.get_revision(hw_version)

        self._read_header()

    def get_data_channels(self, sensors):
        channels = self._revision.get_enabled_channels(sensors)
        channels_with_ts = [EChannelType.TIMESTAMP] + channels
        return channels_with_ts

    def _read_header(self) -> None:
        self._sr = self._read_sample_rate()
        self._sensors = self._read_enabled_sensors()
        self._channels = self._read_data_channels()
        self._channel_dtypes = self._revision.get_channel_dtypes(self._channels)
        self._rtc_diff = self._read_rtc_clock_diff()
        self._start_ts = self._read_start_time()
        self._trial_config = self._read_trial_config()
        self._exg_regs = self._read_exg_regs()
        self._fw_type, self._fw_version = self._read_firmware_version()
        self._exp_board = self._read_expansion_board()
        self._pressure_sensor = self._revision.get_pressure_sensor(
            self._exp_board, self._fw_type, self._fw_version
        )
        self._pressure_calib = self._read_pressure_calib()

        if self.has_sync and not self._revision.is_sd_sync_supported:
            raise NotImplementedError(
                f"Reading synchronized binary files is not supported for "
                f"hardware version {self._revision.hardware_version.name}"
            )

        self._samples_per_block, self._block_size = self._calculate_block_size()

    def _read_hardware_version(self) -> HardwareVersion:
        self._seek(HW_VERSION_OFFSET)
        version_int = self._read_packed(">H")

        version = HardwareVersion.from_int(version_int)
        if version == HardwareVersion.UNKNOWN:
            raise ValueError(
                f"File header specifies unknown hardware version {version_int}"
            )

        return version

    def _read_firmware_version(self) -> tuple[FirmwareType, FirmwareVersion]:
        self._seek(FW_TYPE_OFFSET)
        fw_type = FirmwareType.from_int(self._read_packed(">H"))

        self._seek(FW_VERSION_OFFSET)
        major, minor, rel = self._read_packed(">HBB")

        return fw_type, FirmwareVersion(major=major, minor=minor, rel=rel)

    def _read_expansion_board(self) -> ExpansionBoard:
        self._seek(EXP_BOARD_OFFSET)
        board_id, rev, rev_special = self._read(EXP_BOARD_LEN)

        return ExpansionBoard(board_id=board_id, rev=rev, rev_special=rev_special)

    def _read_pressure_resolution(self) -> int:
        self._seek(PRESSURE_RESOLUTION_OFFSET)
        return (self._read_packed("B") >> 4) & 0x03

    def _read_pressure_calib(self) -> PressureCalibration | None:
        """Read the calibration parameters of the pressure sensor

        :return: The calibration of the pressure sensor, or None if the device did
            not store any parameters
        """
        if self._pressure_sensor == EPressureSensor.BMP581:
            # The BMP581 compensates its readings on the chip
            return BMP581Calibration()

        blocks = self._revision.get_pressure_calib_blocks(self._pressure_sensor)

        block = b""
        for offset, length in blocks:
            self._seek(offset)
            block += self._read(length)

        if not has_calib_params(block):
            return None

        if self._pressure_sensor == EPressureSensor.BMP180:
            return BMP180Calibration(block, self._read_pressure_resolution())
        if self._pressure_sensor == EPressureSensor.BMP280:
            return BMP280Calibration(block)

        return BMP390Calibration(block)

    def _read_sample_rate(self) -> int:
        self._seek(SR_OFFSET)
        return self._read_packed("<H")

    def _read_enabled_sensors(self) -> list[ESensorGroup]:
        self._seek(ENABLED_SENSORS_OFFSET)
        sensor_bitfield = self._read(self._revision.sensorlist_size)
        enabled_sensors = self._revision.deserialize_sensorlist(sensor_bitfield)

        return enabled_sensors

    def _read_data_channels(self) -> list[EChannelType]:
        list_offset = self._revision.sd_channel_list_offset
        if list_offset is None:
            # The revision does not record the channels explicitly. We derive them
            # from the set of enabled sensors instead.
            return self.get_data_channels(self._sensors)

        self._seek(list_offset)
        num_channels = self._read_packed("B")

        max_channels = self._revision.sd_header_len - (list_offset + 1)
        if not 0 < num_channels <= max_channels:
            raise ValueError(
                f"File header specifies invalid number of channels: "
                f"{num_channels} not in [1, {max_channels}]"
            )

        channel_ids = self._read(num_channels)

        channels = [EChannelType.enum_for_id(ch_id) for ch_id in channel_ids]
        return [EChannelType.TIMESTAMP] + channels

    def _read_rtc_clock_diff(self) -> int:
        self._seek(RTC_CLOCK_DIFF_OFFSET)
        rtc_diff_ticks = self._read_packed(">Q")
        return rtc_diff_ticks

    def _read_start_time(self) -> int:
        self._seek(START_TS_OFFSET)
        ts_bin = self._read(START_TS_LEN)

        # The timestamp is 5 byte long in little endian byte order, but has its MSB at
        # offset 0 instead of 4. Due to this, we need to move the last byte back to the
        # end, pad it to 8 bytes and parse it as 64bit value.
        ts_bin_flipped = ts_bin[1:] + ts_bin[0:1]
        ts_bin_padded = ts_bin_flipped + b"\x00" * 3

        ts_ticks = struct.unpack("<Q", ts_bin_padded)
        return unpack(ts_ticks)

    def _read_trial_config(self) -> int:
        self._seek(TRIAL_CONFIG_OFFSET)
        return self._read_packed("<H")

    def _calculate_block_size(self):
        sync_stamp = 9 * self.has_sync
        sample_size = sum([d.size for d in self._channel_dtypes])

        num_samples = int((BLOCK_LEN - sync_stamp) / sample_size)
        block_len = num_samples * sample_size + sync_stamp

        return num_samples, block_len

    def _read_sync_offset(self) -> int | None:
        # For this read operation we assume that every synchronization offset is
        # immediately followed by a timestamp as it is described in the manuals. We
        # need to pair every sync offset with a timestamp for interpolation at a later
        # point in time.
        offset_sign_bool = self._read_packed("B")
        offset_sign = 1 - 2 * offset_sign_bool
        offset_mag = self._read_packed("<Q")

        if offset_mag == 2**64 - 1:
            return None

        offset = offset_sign * offset_mag

        return offset

    def _read_sample(self) -> list:
        ch_values = []

        for ch, dtype in zip(self._channels, self._channel_dtypes):
            val_bin = self._read(dtype.size)
            ch_values.append(dtype.decode(val_bin))

        return ch_values

    def _read_data_block(self) -> tuple[list[list], int]:
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

    def _read_contents(self) -> tuple[list, list[tuple[int, int]]]:
        sync_offsets = []
        samples = []
        sample_ctr = 0

        self._seek(self._revision.sd_header_len)
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

    def _read_exg_regs(self) -> tuple[bytes, bytes]:
        self._seek(EXG_REG_OFFSET)

        reg1 = self._read(EXG_REG_LEN)
        reg2 = self._read(EXG_REG_LEN)
        return reg1, reg2

    def _read_triaxcal_params(
        self, offset: int
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        self._seek(offset)
        calib_param_bytes = self._read(struct.calcsize(TRIAXCAL_FMT))
        params_raw = struct.unpack(TRIAXCAL_FMT, calib_param_bytes)

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

    def has_triaxcal_params(self, sensor: ESensorGroup) -> bool:
        """Check if the file stores calibration parameters for a triaxial sensor

        A device that holds no parameters for a sensor stores a block of zeros or of
        0xFF bytes instead, which cannot be used for calibration.

        :param sensor: The sensor to check
        :return: True if the file holds parameters for the sensor, else False
        """
        spec = self._revision.get_triaxcal_spec(sensor)

        self._seek(spec.offset)
        block = self._read(struct.calcsize(TRIAXCAL_FMT))

        return has_calib_params(block)

    def get_triaxcal_params(
        self, sensor: ESensorGroup
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        spec = self._revision.get_triaxcal_spec(sensor)

        offset, gain, alignment = self._read_triaxcal_params(spec.offset)
        return (
            offset / spec.offset_scaling,
            gain / spec.gain_scaling,
            alignment / spec.alignment_scaling,
        )

    @property
    def hardware_revision(self) -> HardwareRevision:
        return self._revision

    @property
    def firmware_type(self) -> FirmwareType:
        return self._fw_type

    @property
    def firmware_version(self) -> FirmwareVersion:
        return self._fw_version

    @property
    def expansion_board(self) -> ExpansionBoard:
        return self._exp_board

    @property
    def pressure_sensor(self) -> EPressureSensor:
        """The pressure sensor model that is fitted to the recording device"""
        return self._pressure_sensor

    @property
    def pressure_calibration(self) -> PressureCalibration | None:
        """The calibration of the pressure sensor

        :return: The calibration, or None if the device did not store any
            calibration parameters
        """
        return self._pressure_calib

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
    def enabled_sensors(self) -> list[ESensorGroup]:
        return self._sensors

    @property
    def enabled_channels(self) -> list[EChannelType]:
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
