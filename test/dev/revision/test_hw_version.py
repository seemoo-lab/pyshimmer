import pytest

from pyshimmer import HardwareVersion


class TestHardwareVersion:

    def test_version(self):
        assert int(HardwareVersion.SHIMMER3) == 3
        assert int(HardwareVersion.SHIMMER3R) == 10

    def test_from_int(self):
        assert HardwareVersion.from_int(0) == HardwareVersion.SHIMMER1
        assert HardwareVersion.from_int(1) == HardwareVersion.SHIMMER2
        assert HardwareVersion.from_int(2) == HardwareVersion.SHIMMER2R
        assert HardwareVersion.from_int(3) == HardwareVersion.SHIMMER3
        assert HardwareVersion.from_int(10) == HardwareVersion.SHIMMER3R
