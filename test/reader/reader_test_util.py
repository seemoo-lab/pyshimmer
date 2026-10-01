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

import gzip
import struct
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from pyshimmer.dev.channels import EChannelType, ESensorGroup
from pyshimmer.dev.fw_version import FirmwareType
from pyshimmer.dev.gsr import GSR_RANGE_AUTO
from pyshimmer.dev.pressure import EPressureSensor
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
    pressure_calib: bytes = None,
    exp_board: tuple[int, int, int] = (0, 0, 0),
    firmware: tuple[int, int, int, int] = (3, 1, 1, 14),
    gsr_range: int = GSR_RANGE_AUTO,
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
    :param pressure_calib: The calibration block of the pressure sensor
    :param exp_board: The expansion board id, revision, and special revision
    :param firmware: The firmware id, major, minor, and internal version
    :param gsr_range: The range setting of the GSR circuit
    :return: The binary content of the file
    """
    revision = RevisionRegistry.get_revision(HardwareVersion.SHIMMER3R)
    channels = list(channels)

    header = bytearray(revision.sd_header_len)

    header[0x00:0x02] = struct.pack("<H", sample_rate)
    header[0x03 : 0x03 + revision.sensorlist_size] = revision.serialize_sensorlist(
        sensors
    )

    header[0x0B] = gsr_range << 1

    trial_config = 0x04 * sync | 0x02 * master
    header[0x10:0x12] = struct.pack("<H", trial_config)

    header[0x1E:0x20] = struct.pack(">H", HardwareVersion.SHIMMER3R.value)

    fw_id, fw_major, fw_minor, fw_internal = firmware
    header[0x22:0x24] = struct.pack(">H", fw_id)
    header[0x24:0x28] = struct.pack(">HBB", fw_major, fw_minor, fw_internal)

    header[0xD6:0xD9] = bytes(exp_board)
    header[0x2C:0x34] = struct.pack(">Q", rtc_diff)

    header[0x38:0x42] = exg_reg1
    header[0x42:0x4C] = exg_reg2

    if pressure_calib is not None:
        header[0xA0 : 0xA0 + len(pressure_calib)] = pressure_calib

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


@dataclass(frozen=True)
class ConsensysFixture:
    """A binary data file paired with a reference export of its contents

    The reference export is produced by the Shimmer reference tooling and holds the
    calibrated channels of the same recording. It allows us to check the reader
    against a known-good implementation.

    :param name: Base name of the two resource files
    :param device_id: The device id that the reference export prefixes its column
        names with
    :param hw_version: The expected hardware revision of the recording device
    :param fw_type: The expected firmware type of the recording device
    :param fw_version: The expected firmware version as (major, minor, rel)
    :param exp_board: The expected expansion board as (id, rev, rev_special)
    :param pressure_sensor: The expected pressure sensor of the recording device
    :param gsr_range: The expected range setting of the GSR circuit
    :param num_samples: The expected number of samples in the recording
    :param sample_rate: The expected sample rate in Hz
    :param channels: The expected data channels in the order of the file
    :param derived_channels: The channels that post processing is expected to add
    :param columns: Maps the name of a column of the reference export, without the
        device id prefix, to the channel it corresponds to and the factor by which
        the channel must be multiplied to obtain the unit of the column
    """

    name: str
    device_id: str
    hw_version: HardwareVersion
    fw_type: FirmwareType
    fw_version: tuple[int, int, int]
    exp_board: tuple[int, int, int]
    pressure_sensor: EPressureSensor
    gsr_range: int
    num_samples: int
    sample_rate: float
    channels: tuple[EChannelType, ...]
    derived_channels: tuple[EChannelType, ...]
    columns: dict[str, tuple[EChannelType, float]]

    @property
    def bin_path(self) -> Path:
        return get_resources_dir() / f"{self.name}.bin"

    @property
    def csv_path(self) -> Path:
        return get_resources_dir() / f"{self.name}_calibrated.csv.gz"

    def column_name(self, column: str) -> str:
        return f"Shimmer_{self.device_id}_{column}"

    def read_reference(self) -> pd.DataFrame:
        """Read the reference export of this recording

        The export is a tab-separated file that is preceded by a separator hint and
        followed by a row of units.

        :return: The contents of the export as floating point values
        """
        with gzip.open(self.csv_path, "rt") as f:
            df = pd.read_csv(f, sep="\t", skiprows=1)

        # Drop the row of units and the trailing column caused by the line-final
        # separator of the export
        df = df.iloc[1:].reset_index(drop=True)
        df = df[[c for c in df.columns if not c.startswith("Unnamed")]]

        return df.astype(float)


# A Shimmer3R with a GSR+ expansion board: wide-range accelerometer, BMP390
# pressure sensor, PPG, and GSR
FIXTURE_SHIMMER3R_BMP390_GSR = ConsensysFixture(
    name="shimmer3r_bmp390_gsr",
    device_id="86F8",
    hw_version=HardwareVersion.SHIMMER3R,
    fw_type=FirmwareType.LogAndStream,
    fw_version=(1, 1, 14),
    exp_board=(48, 8, 1),
    pressure_sensor=EPressureSensor.BMP390,
    gsr_range=GSR_RANGE_AUTO,
    num_samples=2923,
    sample_rate=51.2,
    # The file header lists pressure before temperature, which matches neither the
    # channel id order nor any static sensor order
    channels=(
        EChannelType.PRESSURE,
        EChannelType.TEMPERATURE,
        EChannelType.ACCEL_WR_X,
        EChannelType.ACCEL_WR_Y,
        EChannelType.ACCEL_WR_Z,
        EChannelType.INTERNAL_ADC_A1,
        EChannelType.GSR_RAW,
    ),
    derived_channels=(
        EChannelType.GSR_RANGE,
        EChannelType.GSR_RESISTANCE,
        EChannelType.GSR_CONDUCTANCE,
    ),
    columns={
        "LIS2DW12_ACC_X_CAL": (EChannelType.ACCEL_WR_X, 1.0),
        "LIS2DW12_ACC_Y_CAL": (EChannelType.ACCEL_WR_Y, 1.0),
        "LIS2DW12_ACC_Z_CAL": (EChannelType.ACCEL_WR_Z, 1.0),
        "GSR_Range_CAL": (EChannelType.GSR_RANGE, 1.0),
        "GSR_Skin_Conductance_CAL": (EChannelType.GSR_CONDUCTANCE, 1.0),
        "GSR_Skin_Resistance_CAL": (EChannelType.GSR_RESISTANCE, 1.0),
        # The reference export reports the PPG channel in mV, we report it in V
        "PPG_A1_CAL": (EChannelType.INTERNAL_ADC_A1, 1000.0),
        # The reference export reports the pressure in kPa, we report it in Pa
        "BMP390_Pressure_CAL": (EChannelType.PRESSURE, 1e-3),
        "BMP390_Temperature_CAL": (EChannelType.TEMPERATURE, 1.0),
    },
)

# A Shimmer3R with an ExG expansion board: wide-range accelerometer and both ExG
# chips in 24 bit mode, driven by their internal test signal
FIXTURE_SHIMMER3R_EXG_24BIT = ConsensysFixture(
    name="shimmer3r_exg_24bit",
    device_id="9A3F",
    hw_version=HardwareVersion.SHIMMER3R,
    fw_type=FirmwareType.LogAndStream,
    fw_version=(1, 1, 15),
    exp_board=(47, 8, 1),
    pressure_sensor=EPressureSensor.BMP390,
    gsr_range=GSR_RANGE_AUTO,
    num_samples=2533,
    sample_rate=51.2,
    channels=(
        EChannelType.ACCEL_WR_X,
        EChannelType.ACCEL_WR_Y,
        EChannelType.ACCEL_WR_Z,
        EChannelType.EXG1_STATUS,
        EChannelType.EXG1_CH1_24BIT,
        EChannelType.EXG1_CH2_24BIT,
        EChannelType.EXG2_STATUS,
        EChannelType.EXG2_CH1_24BIT,
        EChannelType.EXG2_CH2_24BIT,
    ),
    derived_channels=(),
    columns={
        "LIS2DW12_ACC_X_CAL": (EChannelType.ACCEL_WR_X, 1.0),
        "LIS2DW12_ACC_Y_CAL": (EChannelType.ACCEL_WR_Y, 1.0),
        "LIS2DW12_ACC_Z_CAL": (EChannelType.ACCEL_WR_Z, 1.0),
        "ECG_EMG_Status1_CAL": (EChannelType.EXG1_STATUS, 1.0),
        "ECG_EMG_Status2_CAL": (EChannelType.EXG2_STATUS, 1.0),
        # The reference export reports the ExG channels in mV, we report them in V
        "Test_CHIP1_CH1_24BIT_CAL": (EChannelType.EXG1_CH1_24BIT, 1000.0),
        "Test_CHIP1_CH2_24BIT_CAL": (EChannelType.EXG1_CH2_24BIT, 1000.0),
        "Test_CHIP2_CH1_24BIT_CAL": (EChannelType.EXG2_CH1_24BIT, 1000.0),
        "Test_CHIP2_CH2_24BIT_CAL": (EChannelType.EXG2_CH2_24BIT, 1000.0),
    },
)

# A Shimmer3 with a GSR+ expansion board: wide-range accelerometer, PPG, and GSR.
# Unlike the Shimmer3R, this revision does not record a channel list, so the case
# also covers deriving the channels from the enabled sensors.
FIXTURE_SHIMMER3_GSR_PPG = ConsensysFixture(
    name="shimmer3_gsr_ppg",
    device_id="3E36",
    hw_version=HardwareVersion.SHIMMER3,
    fw_type=FirmwareType.LogAndStream,
    fw_version=(1, 1, 4),
    exp_board=(48, 4, 2),
    # The board revision is new enough for the second generation of IMU sensors
    pressure_sensor=EPressureSensor.BMP280,
    gsr_range=GSR_RANGE_AUTO,
    num_samples=4527,
    sample_rate=51.2,
    channels=(
        EChannelType.INTERNAL_ADC_A1,
        EChannelType.GSR_RAW,
        EChannelType.ACCEL_WR_X,
        EChannelType.ACCEL_WR_Y,
        EChannelType.ACCEL_WR_Z,
    ),
    derived_channels=(
        EChannelType.GSR_RANGE,
        EChannelType.GSR_RESISTANCE,
        EChannelType.GSR_CONDUCTANCE,
    ),
    columns={
        "Accel_WR_X_CAL": (EChannelType.ACCEL_WR_X, 1.0),
        "Accel_WR_Y_CAL": (EChannelType.ACCEL_WR_Y, 1.0),
        "Accel_WR_Z_CAL": (EChannelType.ACCEL_WR_Z, 1.0),
        "GSR_Range_CAL": (EChannelType.GSR_RANGE, 1.0),
        "GSR_Skin_Conductance_CAL": (EChannelType.GSR_CONDUCTANCE, 1.0),
        "GSR_Skin_Resistance_CAL": (EChannelType.GSR_RESISTANCE, 1.0),
        # The reference export reports the PPG channel in mV, we report it in V
        "PPG_A13_CAL": (EChannelType.INTERNAL_ADC_A1, 1000.0),
    },
)

CONSENSYS_FIXTURES = [
    FIXTURE_SHIMMER3_GSR_PPG,
    FIXTURE_SHIMMER3R_BMP390_GSR,
    FIXTURE_SHIMMER3R_EXG_24BIT,
]
