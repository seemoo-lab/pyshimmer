# Reader test resources

Binary data files recorded by Shimmer devices, used by the tests of the Reader API.
Some are paired with an export of the same recording produced by the Shimmer
reference tooling, which lets the tests compare the reader against a known-good
implementation instead of only against our reading of the file format.

The exports are tab separated, are preceded by a separator hint, and carry a row of
units below the header row. Their column names are prefixed with the id of the
recording device.

## Shimmer3

| File | Reference export | Contents |
| --- | --- | --- |
| `single_sample.bin` | none | Low-noise accelerometer, battery, and PPG |
| `pair_raw.bin` | `pair_consensys.csv` | Low-noise accelerometer, battery, and PPG. The export holds the **uncalibrated** PPG channel. |
| `sdlog_sync_slave.bin` | `sdlog_sync_slave.csv.gz` | PPG of a synchronized trial, recorded by a slave device. The export holds the **uncalibrated** PPG channel. |
| `triaxcal_sample.bin` | `triaxcal_uncalibrated.csv.gz`, `triaxcal_calibrated.csv.gz` | All four triaxial sensors, for the kinematic calibration |
| `ecg.bin` | `ecg_uncalibrated.csv.gz`, `ecg_calibrated.csv.gz` | ExG in 24 bit mode |
| `shimmer3_gsr_ppg.bin` | `shimmer3_gsr_ppg_calibrated.csv.gz` | GSR+ expansion board (SR48-4-2), firmware v1.1.4. Wide-range accelerometer, PPG, and GSR. The Shimmer3 does not record a channel list, so this also covers deriving the set and order of channels from the enabled sensors. It carries no pressure channels, so the BMP280 is **not** covered. |

## Shimmer3R

Both recordings were made with LogAndStream and are not synchronized. See
`CONSENSYS_FIXTURES` in `reader_test_util.py` for the properties that the tests
expect of these and of the Shimmer3 recording above.

| File | Reference export | Contents |
| --- | --- | --- |
| `shimmer3r_bmp390_gsr.bin` | `shimmer3r_bmp390_gsr_calibrated.csv.gz` | GSR+ expansion board (SR48-8-1), firmware v1.1.14. Wide-range accelerometer, BMP390 pressure and temperature, PPG, and GSR. The file header lists pressure before temperature, so it also covers the header-driven channel order. |
| `shimmer3r_exg_24bit.bin` | `shimmer3r_exg_24bit_calibrated.csv.gz` | ExG expansion board (SR47-8-1), firmware v1.1.15. Wide-range accelerometer and both ExG chips in 24 bit mode. The ExG front-end runs on its internal test signal, so the values are not physiological. Roughly half the samples are negative, which covers the signed 24 bit decoding. All four channels use a gain of 1, so the gain divisor is **not** covered. |
