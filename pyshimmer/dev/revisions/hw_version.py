from __future__ import annotations

from enum import IntEnum

from .revision import HardwareRevision
from .shimmer3 import REV_SHIMMER3


class HardwareVersion(IntEnum):
    """Represents the supported Shimmer device hardware version / revision

    This enum links between the value returned by the Shimmer device
    and the revision class.
    """

    SHIMMER1 = (0, None)
    SHIMMER2 = (1, None)
    SHIMMER2R = (2, None)
    SHIMMER3 = (3, REV_SHIMMER3)
    SHIMMER3R = (10, None)
    UNKNOWN = (-1, None)

    def __new__(cls, version: int, revision: HardwareRevision | None):
        # Strips the revision argument from the tuple and only assigns the
        # version ID as enum value
        obj = int.__new__(cls, version)
        obj._value_ = version
        obj._revision = revision
        return obj

    @classmethod
    def from_int(cls, value: int) -> HardwareVersion:
        """Converts an Integer to the corresponding HardwareVersion enum

        :param value: Integer representing device hardware version
        :return: Corresponding HardwareVersion enum member, or UNKNOWN if unrecognised
        """
        return cls._value2member_map_.get(value, cls.UNKNOWN)

    @property
    def revision(self) -> HardwareRevision | None:
        return self._revision

    def get_revision(self) -> HardwareRevision:
        """Provides a fail-early way of retrieving the revision

        :return: A revision if one is available. Otherwise, it throws a
            ValueError.
        """
        if self._revision is None:
            raise ValueError(f"Hardware version {self.value} does not have revision")

        return self._revision
