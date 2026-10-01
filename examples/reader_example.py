from __future__ import annotations

import sys
from datetime import datetime, timezone

import numpy as np

from pyshimmer import ESensorGroup, ShimmerBinaryReader, ShimmerReader

# A binary file recorded by a Shimmer device. On the SD card of the device, the files
# of a trial are stored as
#
#   <trial name>/<device name>-<session>/<file number>
#
# where the file number is a zero-padded counter, i.e. 000, 001, and so forth. Both
# Shimmer3 and Shimmer3R files are supported. The hardware revision is read from the
# file header, so no configuration is necessary.
DEFAULT_FILE_PATH = "test/reader/resources/ecg.bin"


def main(args=None):
    args = args if args is not None else sys.argv[1:]
    file_path = args[0] if args else DEFAULT_FILE_PATH

    with open(file_path, "rb") as f:
        # The binary reader provides access to the configuration header of the file.
        # Creating it separately is optional, ShimmerReader creates one internally if
        # it is only given the file object.
        bin_reader = ShimmerBinaryReader(f)
        reader = ShimmerReader(bin_reader=bin_reader)

        # Read the entire file into memory and apply the calibration parameters that
        # are stored in the file header
        reader.load_file_data()

        revision = reader.hardware_revision
        print(f"File: {file_path}")
        print(f"Hardware revision: {revision.hardware_version.name}")
        print(f"Sampling rate: {reader.sample_rate:.4f} Hz")
        print(
            f"Firmware: {bin_reader.firmware_type.name} "
            f"{bin_reader.firmware_version.major}."
            f"{bin_reader.firmware_version.minor}."
            f"{bin_reader.firmware_version.rel}"
        )
        print(f"Enabled sensors: {[s.name for s in bin_reader.enabled_sensors]}")
        print(f"Synchronized trial: {bin_reader.has_sync}")

        if ESensorGroup.PRESSURE in bin_reader.enabled_sensors:
            # The pressure channels are only reported in Pa and degrees Celsius if
            # the device stored the calibration coefficients of its pressure sensor
            calib = bin_reader.pressure_calibration
            print(
                f"Pressure sensor: {calib.sensor.name}, "
                f"calibrated: {not calib.is_blank}"
            )
        print()

        ts = reader.timestamp
        print(f"Number of samples: {len(ts)}")
        print(f"Recording duration: {ts[-1] - ts[0]:.3f} s")

        # If the device clock was set, the timestamps are absolute Unix timestamps.
        # Otherwise, they are relative to the boot-up time of the device.
        if bin_reader.has_global_clock:
            start = datetime.fromtimestamp(ts[0], tz=timezone.utc)
            print(f"Recording start: {start.isoformat()}")
        else:
            print("Recording start: unknown, the device clock was not set")
        print()

        print(f"{'Channel':<16} {'Minimum':>12} {'Maximum':>12} {'Mean':>12}")
        for channel in reader.channels:
            y = reader[channel]
            print(
                f"{channel.name:<16} {y.min():>12.3f} {y.max():>12.3f} "
                f"{y.mean():>12.3f}"
            )
        print()

        # Sanity check: while the device is at rest, the magnitude of the calibrated
        # low-noise accelerometer should be close to the gravitational acceleration
        if ESensorGroup.ACCEL_LN in bin_reader.enabled_sensors:
            accel_channels = revision.get_enabled_channels([ESensorGroup.ACCEL_LN])

            if all(c in reader.channels for c in accel_channels):
                accel = np.stack([reader[c] for c in accel_channels])
                magnitude = np.linalg.norm(accel, axis=0)
                print(
                    f"Median accelerometer magnitude: "
                    f"{np.median(magnitude):.3f} m/s^2"
                )


if __name__ == "__main__":
    main()
