# Changelog

This changelog tries to follow [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
The project uses semantic versioning.

## Next Release

### Added
- Support for reading binary files recorded by a Shimmer3R. The reader now
  determines the hardware revision from the file header and adapts the header
  length, the channel layout, and the calibration parameter offsets accordingly.
  The hardware revision can be provided explicitly via the new `hw_version`
  parameter of `ShimmerBinaryReader` and `ShimmerReader` for files whose header
  does not carry a usable version field.
- Data types for the Shimmer3R high-g accelerometer and alternative
  magnetometer channels, along with the new `PackedChannelDataType` class for
  channels whose value is left-aligned within a larger word.
- The `TriaxCalibSpec` class, which describes the location and scaling of a
  triaxial calibration block within a data file.
- An example that reads a binary file and prints its metadata and channel
  statistics, see `examples/reader_example.py`.
- Compensation of the barometric pressure and temperature channels. The reader
  now reports them in kPa and degrees Celsius instead of raw ADC counts. The
  BMP180, BMP280, BMP390, and BMP581 are supported, and the sensor model is
  determined from the hardware revision, the expansion board, and the firmware
  version recorded in the file header.
- The reader now parses the firmware version and the expansion board details
  from the file header and exposes them as `ShimmerBinaryReader.firmware_type`,
  `firmware_version`, and `expansion_board`.
- Tests that compare the reader against exports of the Shimmer reference
  tooling for three recordings: a Shimmer3 covering the PPG and GSR channels
  and the channel order derived from the enabled sensors, and two Shimmer3R
  covering the BMP390, PPG, and GSR channels and the ExG channels in 24 bit
  mode. Unlike the synthetic test files, these check the reader against a
  known-good implementation on data written by an actual device. See
  `test/reader/resources/README.md` for the provenance of the files.
- Conversion of the galvanic skin response channel. The raw channel encodes the
  active range of the GSR circuit alongside the ADC reading. The reader keeps it
  and adds the range, the skin resistance in kOhm, and the skin conductance in
  microsiemens as derived channels, see `ShimmerReader.derived_channels`. A
  reading below the reference voltage of the amplifier means that the electrodes
  are open, and reads as about 4.5 GOhm on every range. The conversion follows
  the range setting that the device stored in the file header, see
  `ShimmerBinaryReader.gsr_range`. On a fixed range, the resistance is clamped to
  the limits of that range.

### Changed
- Binary files recorded by a Shimmer3R store the set and order of their data
  channels in the file header. The reader now uses that list instead of
  deriving the channels from the enabled sensors.
- The hardware revision classes now describe the layout of a binary data file.
  As a consequence, the calibration offset constants were removed from
  `pyshimmer.reader.reader_const` and replaced by `HardwareRevision`
  properties.
- Reading a synchronized Shimmer3R recording now raises `NotImplementedError`
  instead of returning incorrectly parsed data. Synchronized Shimmer3
  recordings are unaffected.
- The sensor order of the Shimmer3R was corrected. It previously used the order
  of the Shimmer3, which contradicts the channel ids assigned by the Shimmer3R
  firmware.
- Format code base with black
- Wrap long lines to 90 characters
- Replace types from typing with built-in ones
- Raise required Python version to 3.9 since PEP 604 is used in the code
- Update the `ChannelDataType` class to use the `int.from_bytes` and
  `int.to_bytes` methods
- Introduce new hardware revision classes to encapsulate all hardware-specific
  code. As a consequence, all global functions in `pyshimmer.dev.base` and
  `pyshimmer.dev.channels` were removed.

### Fixed
- The PPG channel was scaled by dividing the raw reading by 1000, which treated
  the ADC counts as if they were millivolts. The channel is connected to a 12bit
  ADC with a 3V reference, so the readings are now scaled accordingly. Values
  reported for this channel change by a factor of about 0.73.
- Calibrating a triaxial sensor for which the device stored no calibration
  parameters raised a `LinAlgError`, because the empty parameter block yields a
  singular calibration matrix. The channels of such a sensor are now left
  uncalibrated. See `ShimmerBinaryReader.has_triaxcal_params`.

## 1.0.0 - 2025-10-25

This is a rebrand of release v0.7.0 as v1.0.0.

A lot of incoming changes and modifications already present on the main branch
make the future code base incompatible to previous releases, such as v0.7.0.
I would like to make the state that is v0.7.0 the official version 1.0.0 of
pyshimmer. That way, it will be easier for users to switch between this first
version and the newer modifications that are going to lead to version 2.0.0.

## 0.7.0 - 2025-01-18

First release with Changelog

### Added
- This Changelog :)

### Changed
- The CI workflow now builds and deploys the artifacts

