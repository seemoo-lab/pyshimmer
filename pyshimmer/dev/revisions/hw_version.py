from __future__ import annotations

from enum import IntEnum


class HardwareVersion(IntEnum):
    """Represents the supported Shimmer device hardware version / revision

    This enum links between the value returned by the Shimmer device
    and the revision class.
    """

    SHIMMER1 = 0
    SHIMMER2 = 1
    SHIMMER2R = 2
    SHIMMER3 = 3
    SHIMMER3R = 10
    UNKNOWN = -1

    @classmethod
    def from_int(cls, value: int) -> HardwareVersion:
        """Converts an Integer to the corresponding HardwareVersion enum

        :param value: Integer representing device hardware version
        :return: Corresponding HardwareVersion enum member, or UNKNOWN if unrecognised
        """
        return cls._value2member_map_.get(value, cls.UNKNOWN)
