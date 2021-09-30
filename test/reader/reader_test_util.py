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
from pathlib import Path

_res_folder_name = 'resources'
_single_sample_name = 'single_sample.bin'
_synced_pair_bin_name = 'sdlog_sync_slave.bin'
_synced_pair_csv_name = 'sdlog_sync_slave.csv.gz'
_pair_raw_name = 'pair_raw.bin'
_pair_csv_name = 'pair_consensys.csv'

_acc_gyro_sample_name = "triaxcal_sample.bin"
_acc_gyro_uncal_name = "triaxcal_uncalibrated.csv.gz"
_acc_gyro_cal_name = "triaxcal_calibrated.csv.gz"

_ecg_sample_bin = 'ecg.bin'
_ecg_sample_uncal = 'ecg_uncalibrated.csv.gz'
_ecg_sample_cal = 'ecg_calibrated.csv.gz'


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
    return res_dir / _ecg_sample_bin, res_dir / _ecg_sample_uncal, res_dir / _ecg_sample_cal


def get_triaxcal_sample():
    res_dir = get_resources_dir()
    return res_dir / _acc_gyro_sample_name, res_dir / _acc_gyro_uncal_name, res_dir / _acc_gyro_cal_name
