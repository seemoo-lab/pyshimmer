import pytest

from pyshimmer import HardwareVersion


class TestHardwareVersion:

    def test_revision_access(self):
        ver_shimmer3 = HardwareVersion.SHIMMER3
        assert ver_shimmer3.revision is not None
        assert ver_shimmer3.revision is ver_shimmer3.get_revision()

        ver_shimmer2 = HardwareVersion.SHIMMER2
        assert ver_shimmer2.revision is None
        with pytest.raises(ValueError):
            ver_shimmer2.get_revision()
