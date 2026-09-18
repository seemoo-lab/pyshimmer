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
from collections.abc import Iterable
from pathlib import Path

from pyshimmer.dev.channels import EChannelType, ESensorGroup
from pyshimmer.dev.revisions import RevisionRegistry, HardwareVersion

_res_folder_name = "resources"
_single_sample_name = "single_sample.bin"
_synced_pair_bin_name = "sdlog_sync_slave.bin"
_synced_pair_csv_name = "sdlog_sync_slave.csv.gz"
_pair_raw_name = "pair_raw.bin"
_pair_csv_name = "pair_consensys.csv"

_acc_gyro_sample_name = "triaxcal_sample.bin"
_acc_gyro_uncal_name = "triaxcal_uncalibrated.csv.gz"
_acc_gyro_cal_name = "triaxcal_calibrated.csv.gz"

_ecg_sample_bin = "ecg.bin"
_ecg_sample_uncal = "ecg_uncalibrated.csv.gz"
_ecg_sample_cal = "ecg_calibrated.csv.gz"


def get_resources_dir():
    my_dir = Path(__file__).parent
    res_dir = my_dir / _res_folder_name
    return res_dir


def get_binary_sample_fpath():
    return get_resources_dir() / _single_sample_name


def get_bin_vs_consensys_pair_fpath():
    res_dir = get_resources_dir()
    return res_dir / _pair_raw_name, res_dir / _pair_csv_name


def get_synced_bin_vs_consensys_pair_fpath():
    res_dir = get_resources_dir()
    return res_dir / _synced_pair_bin_name, res_dir / _synced_pair_csv_name


def get_ecg_sample():
    res_dir = get_resources_dir()
    return (
        res_dir / _ecg_sample_bin,
        res_dir / _ecg_sample_uncal,
        res_dir / _ecg_sample_cal,
    )


def get_triaxcal_sample():
    res_dir = get_resources_dir()
    return (
        res_dir / _acc_gyro_sample_name,
        res_dir / _acc_gyro_uncal_name,
        res_dir / _acc_gyro_cal_name,
    )


def encode_triaxcal_block(
    offset: Iterable[int], gain: Iterable[int], alignment: Iterable[int]
) -> bytes:
    """Encode a set of calibration parameters as 21 byte calibration block

    :param offset: The three offset values
    :param gain: The three gain values
    :param alignment: The nine alignment matrix entries in row-major order
    :return: The encoded calibration block
    """
    return struct.pack(">6h9b", *offset, *gain, *alignment)


def build_shimmer3r_file(
    channels: Iterable[EChannelType],
    samples: Iterable[Iterable[int]],
    sensors: Iterable[ESensorGroup] = (),
    sample_rate: int = 64,
    start_ts: int = 0,
    rtc_diff: int = 0,
    sync: bool = False,
    master: bool = False,
    exg_reg1: bytes = b"\x00" * 10,
    exg_reg2: bytes = b"\x00" * 10,
    triaxcal: dict[ESensorGroup, bytes] = None,
) -> bytes:
    """Assemble a synthetic Shimmer3R binary file

    The file layout follows the Shimmer3R SD header as it is parsed by the Java
    reference implementation: a 384 byte configuration header followed by the sample
    data. The header carries an explicit channel list which determines the set and
    order of the recorded channels.

    :param channels: The recorded data channels, excluding the timestamp
    :param samples: One sequence of channel values per sample. Each sequence holds the
        timestamp followed by one value per entry in channels.
    :param sensors: The sensors to mark as enabled in the sensor bitfield
    :param sample_rate: The device-specific sample rate to record in the header
    :param start_ts: The initial timestamp of the recording in clock ticks
    :param rtc_diff: The difference between device clock and real-time clock in ticks
    :param sync: True to set the synchronization flag in the trial configuration
    :param master: True to set the sync master flag in the trial configuration
    :param exg_reg1: The content of the first ExG register bank
    :param exg_reg2: The content of the second ExG register bank
    :param triaxcal: Calibration blocks to place in the header, by sensor
    :return: The binary content of the file
    """
    revision = RevisionRegistry.get_revision(HardwareVersion.SHIMMER3R)
    channels = list(channels)

    header = bytearray(revision.sd_header_len)

    header[0x00:0x02] = struct.pack("<H", sample_rate)
    header[0x03 : 0x03 + revision.sensorlist_size] = revision.serialize_sensorlist(
        sensors
    )

    trial_config = 0x04 * sync | 0x02 * master
    header[0x10:0x12] = struct.pack("<H", trial_config)

    header[0x1E:0x20] = struct.pack(">H", HardwareVersion.SHIMMER3R.value)
    header[0x2C:0x34] = struct.pack(">Q", rtc_diff)

    header[0x38:0x42] = exg_reg1
    header[0x42:0x4C] = exg_reg2

    for sensor, block in (triaxcal or {}).items():
        block_offset = revision.get_triaxcal_spec(sensor).offset
        header[block_offset : block_offset + len(block)] = block

    # The initial timestamp is stored as five byte little endian value, but with its
    # most significant byte moved to the front
    ts_bin = start_ts.to_bytes(5, byteorder="little")
    header[0xFB:0x100] = ts_bin[4:5] + ts_bin[0:4]

    list_offset = revision.sd_channel_list_offset
    header[list_offset] = len(channels)
    header[list_offset + 1 : list_offset + 1 + len(channels)] = bytes(
        ch.channel_id for ch in channels
    )

    all_channels = [EChannelType.TIMESTAMP] + channels
    dtypes = revision.get_channel_dtypes(all_channels)

    data = bytearray()
    for sample in samples:
        for dtype, value in zip(dtypes, sample):
            data += dtype.encode(value)

    return bytes(header) + bytes(data)
