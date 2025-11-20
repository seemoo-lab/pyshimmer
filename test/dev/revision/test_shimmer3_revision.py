# pyshimmer - API for Shimmer sensor devices
# Copyright (C) 2025  Lukas Magel

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

import pytest
import numpy as np

from pyshimmer import Shimmer3Revision


class TestShimmer3Revision:

    @pytest.fixture
    def revision(self) -> Shimmer3Revision:
        return Shimmer3Revision()

    def test_sr2dr(self, revision: Shimmer3Revision):
        r = revision.sr2dr(1024.0)
        assert r == 32

        r = revision.sr2dr(500.0)
        assert r == 66

    def test_dr2sr(self, revision: Shimmer3Revision):
        r = revision.dr2sr(65)
        assert r == pytest.approx(504, abs=0.5)

        r = revision.dr2sr(32)
        assert r == 1024.0

        r = revision.dr2sr(64)
        assert r == 512.0

    def test_sec2ticks(self, revision: Shimmer3Revision):
        r = revision.sec2ticks(1.0)
        assert r == 32768

        r = revision.sec2ticks(np.array([1.0, 2.0]))
        np.testing.assert_array_equal(r, np.array([32768, 65536]))

    def test_ticks2sec(self, revision: Shimmer3Revision):
        r = revision.ticks2sec(32768)
        assert r == 1.0

        r = revision.ticks2sec(65536)
        assert r == 2.0

        i = np.array([32768, 65536])
        r = revision.ticks2sec(i)
        np.testing.assert_array_equal(r, np.array([1.0, 2.0]))
