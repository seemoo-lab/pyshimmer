import pytest

from pyshimmer import (
    RevisionRegistry,
    HardwareVersion,
    Shimmer3Revision,
    Shimmer3RRevision,
)


class TestRegistry:

    def test_find_revision(self):
        rev = RevisionRegistry.find_revision(HardwareVersion.SHIMMER3)
        assert isinstance(rev, Shimmer3Revision)
        assert rev.hardware_version == HardwareVersion.SHIMMER3

        rev = RevisionRegistry.find_revision(HardwareVersion.SHIMMER3R)
        assert isinstance(rev, Shimmer3RRevision)
        assert rev.hardware_version == HardwareVersion.SHIMMER3R

        rev = RevisionRegistry.find_revision(HardwareVersion.SHIMMER2)
        assert rev is None

    def test_get_revision(self):
        rev = RevisionRegistry.find_revision(HardwareVersion.SHIMMER3)
        assert isinstance(rev, Shimmer3Revision)
        assert rev.hardware_version == HardwareVersion.SHIMMER3

        with pytest.raises(ValueError):
            RevisionRegistry.get_revision(HardwareVersion.SHIMMER1)
