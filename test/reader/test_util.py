# pyshimmer - API for Shimmer sensor devices
# Copyright (C) 2020  Lukas Magel

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

from unittest import TestCase

import numpy as np

from pyshimmer.reader.shimmer_reader import fit_linear_1d


class UtilTest(TestCase):

    def test_fit_linear_1d(self):
        x = np.array([0, 1])
        y = np.array([0, 10])
        xi = np.array([0, 0.25, 0.5, 0.75, 1])

        yi_expected = np.array([0, 2.5, 5, 7.5, 10])
        yi_actual = fit_linear_1d(x, y, xi)
        np.testing.assert_almost_equal(yi_actual, yi_expected)

        xi = 0.1
        yi_expected = 1.0
        yi_actual = fit_linear_1d(x, y, xi)
        np.testing.assert_almost_equal(yi_actual, yi_expected)
