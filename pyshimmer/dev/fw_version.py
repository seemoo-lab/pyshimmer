# pyshimmer - API for Shimmer sensor devices
# Copyright (C) 2023  Lukas Magel

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

from enum import IntEnum
from .revisions import HardwareRevision, HardwareVersion


def ensure_firmware_version(func):
    def wrapper(self, other):
        if not isinstance(other, FirmwareVersion):
            return False

        return func(self, other)

    return wrapper


class FirmwareVersion:

    def __init__(self, major: int, minor: int, rel: int):
        """Represents the version of the Shimmer firmware

        :param major: Major version
        :param minor: Minor version
        :param rel: Patch level
        """
        self.major = major
        self.minor = minor
        self.rel = rel
        self._key = (major, minor, rel)

    @ensure_firmware_version
    def __eq__(self, other: FirmwareVersion) -> bool:
        return self._key == other._key

    @ensure_firmware_version
    def __gt__(self, other: FirmwareVersion) -> bool:
        return self._key > other._key

    @ensure_firmware_version
    def __ge__(self, other: FirmwareVersion) -> bool:
        return self._key >= other._key

    @ensure_firmware_version
    def __lt__(self, other: FirmwareVersion) -> bool:
        return self._key < other._key

    @ensure_firmware_version
    def __le__(self, other: FirmwareVersion) -> bool:
        return self._key <= other._key


class FirmwareType(IntEnum):
    BtStream = 0x01
    SDLog = 0x02
    LogAndStream = 0x03
    Unknown = -1

    @classmethod
    def from_int(cls, value: int) -> FirmwareType:
        """Converts an Integer to the corresponding FirmwareType enum

        :param value: Integer representing firmware type
        :return: Corresponding FirmwareType enum member, or Unknown if unrecognised
        """
        return cls._value2member_map_.get(value, cls.Unknown)


class FirmwareCapabilities:

    def __init__(
        self,
        hw_revision: HardwareRevision,
        fw_type: FirmwareType,
        version: FirmwareVersion,
    ):
        self._revision = hw_revision
        self._fw_type = fw_type
        self._version = version

    @property
    def hardware_revision(self) -> HardwareRevision:
        return self._revision

    @property
    def fw_type(self) -> FirmwareType:
        return self._fw_type

    @property
    def version(self) -> FirmwareVersion:
        return self._version

    @property
    def supports_ack_disable(self) -> bool:
        return (
            self._fw_type == FirmwareType.LogAndStream
            and self._version >= FirmwareVersion(major=0, minor=15, rel=4)
        )

    @property
    def status_byte_count(self) -> int:
        """The number of status bytes the firmware sends in a status response

        Shimmer3R LogAndStream firmware sends a second status byte, which holds the
        USB plugged-in state, from version 1.0.24 on. All other firmware sends one.
        Shimmer3 and Shimmer3R version numbers overlap, so the hardware revision
        decides as much as the version.
        """
        if (
            self._revision.hardware_version == HardwareVersion.SHIMMER3R
            and self._fw_type == FirmwareType.LogAndStream
            and self._version >= FirmwareVersion(major=1, minor=0, rel=24)
        ):
            return 2

        return 1
