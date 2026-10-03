# Changelog

This changelog tries to follow [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
The project uses semantic versioning.

## Next Release

### Changed
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
- From LogAndStream v1.0.24 on, the Shimmer3R sends a second status byte, which
  holds the USB plugged-in state. The Bluetooth API read only the first and took
  the second for the start of the next message. That misaligned a data stream,
  or stopped the read loop and left every later command blocked. The number of
  status bytes now follows the hardware revision and the firmware version, see
  `HardwareRevision.get_status_byte_count`.

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

