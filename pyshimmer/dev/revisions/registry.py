# pyshimmer - API for Shimmer sensor devices
# Copyright (C) 2026  Lukas Magel

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

from .hw_version import HardwareVersion
from .revision import HardwareRevision
from .shimmer3 import Shimmer3Revision
from .shimmer3r import Shimmer3RRevision


class RevisionRegistry:

    REV_SHIMMER3 = Shimmer3Revision()
    REV_SHIMMER3R = Shimmer3RRevision()

    _MAP = {
        HardwareVersion.SHIMMER3: REV_SHIMMER3,
        HardwareVersion.SHIMMER3R: REV_SHIMMER3R,
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
