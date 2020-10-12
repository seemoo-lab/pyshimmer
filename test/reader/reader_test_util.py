from pathlib import Path

_res_folder_name = 'resources'
_single_sample_name = 'single_sample.bin'
_synced_pair_bin_name = 'sdlog_sync_slave.bin'
_synced_pair_csv_name = 'sdlog_sync_slave.csv.gz'
_pair_raw_name = 'pair_raw.bin'
_pair_csv_name = 'pair_consensys.csv'

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
