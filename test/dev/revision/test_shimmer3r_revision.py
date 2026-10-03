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

import pytest

from pyshimmer import Shimmer3RRevision, FirmwareType, FirmwareVersion


class TestShimmer3RRevision:

    @pytest.fixture
    def revision(self) -> Shimmer3RRevision:
        return Shimmer3RRevision()

    @pytest.mark.parametrize(
        "fw_type, fw_version, expected",
        [
            # LogAndStream adds the USB plugged-in state as a second byte from v1.0.24
            (FirmwareType.LogAndStream, FirmwareVersion(1, 0, 24), 2),
            (FirmwareType.LogAndStream, FirmwareVersion(1, 1, 0), 2),
            (FirmwareType.LogAndStream, FirmwareVersion(2, 0, 0), 2),
            (FirmwareType.LogAndStream, FirmwareVersion(1, 0, 23), 1),
            (FirmwareType.LogAndStream, FirmwareVersion(0, 0, 2), 1),
            # Other firmware does not
            (FirmwareType.SDLog, FirmwareVersion(1, 0, 24), 1),
            (FirmwareType.BtStream, FirmwareVersion(1, 0, 24), 1),
            (FirmwareType.Unknown, FirmwareVersion(1, 0, 24), 1),
        ],
    )
    def test_get_status_byte_count(
        self,
        revision: Shimmer3RRevision,
        fw_type: FirmwareType,
        fw_version: FirmwareVersion,
        expected: int,
    ):
        assert revision.get_status_byte_count(fw_type, fw_version) == expected
