from .hw_version import HardwareVersion
from .revision import HardwareRevision
from .shimmer3 import Shimmer3Revision
from .shimmer3r import Shimmer3RRevision


class RevisionRegistry:

    _MAP = {
        HardwareVersion.SHIMMER3: Shimmer3Revision(),
        HardwareVersion.SHIMMER3R: Shimmer3RRevision(),
    }

    ALL_REVISIONS = tuple(_MAP.values())

    @classmethod
    def find_revision(cls, version: HardwareVersion) -> HardwareRevision | None:
        return cls._MAP.get(version, None)

    @classmethod
    def get_revision(cls, version: HardwareVersion) -> HardwareRevision:
        rev = cls.find_revision(version)
        if rev is None:
            raise ValueError(f"No revision exists for hardware version {version.name}")

        return rev
