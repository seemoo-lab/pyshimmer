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

import numpy as np

import pytest

from pyshimmer.dev.gsr import calibrate_gsr, split_gsr_raw


class TestSplitGsrRaw:

    def test_split(self):
        # The two most significant bits of the channel value hold the active range
        raw = np.array([697, 17188, 33869, 50567])

        gsr_range, adc_value = split_gsr_raw(raw)

        np.testing.assert_equal(gsr_range, np.array([0, 1, 2, 3]))
        np.testing.assert_equal(adc_value, np.array([697, 804, 1101, 1415]))

    def test_split_accepts_scalars(self):
        gsr_range, adc_value = split_gsr_raw(17188)

        assert gsr_range == 1
        assert adc_value == 804


class TestCalibrateGsr:

    # Raw channel values and the resistance and conductance that the Shimmer
    # reference tooling reports for them, one sample per range
    RAW = np.array([697, 17188, 33869, 50567])
    EXP_RANGE = np.array([0, 1, 2, 3])
    EXP_RESISTANCE = np.array(
        [
            1892.1724137931103,
            1612.1604938271603,
            1630.8243727598565,
            3074.7440273037537,
        ]
    )
    EXP_CONDUCTANCE = np.array(
        [
            0.5284930658064968,
            0.6202856377072405,
            0.6131868131868133,
            0.3252303252303253,
        ]
    )

    def test_calibrate(self):
        gsr_range, resistance, conductance = calibrate_gsr(self.RAW)

        np.testing.assert_equal(gsr_range, self.EXP_RANGE)
        np.testing.assert_allclose(resistance, self.EXP_RESISTANCE, rtol=0, atol=1e-9)
        np.testing.assert_allclose(
            conductance, self.EXP_CONDUCTANCE, rtol=0, atol=1e-12
        )

    # Range 3 at the open circuit limit, 3300 kOhm / (683 * 3V / 4095 / 0.5V - 1),
    # about 4.5 GOhm
    OPEN_RESISTANCE = 3300.0 * 4095 / 3

    def test_reading_below_reference_reads_open_on_every_range(self):
        # A reading below the amplifier reference has no positive resistance, so
        # the electrodes are open. It must not be raised to the lowest resistance
        # the circuit can measure, which would report the highest conductance.
        raw = np.array([(g << 14) | adc for g in range(4) for adc in (0, 682)])

        gsr_range, resistance, conductance = calibrate_gsr(raw)

        np.testing.assert_equal(gsr_range, np.repeat(np.arange(4), 2))
        np.testing.assert_allclose(resistance, self.OPEN_RESISTANCE, rtol=1e-12)
        np.testing.assert_allclose(conductance, 1000.0 / self.OPEN_RESISTANCE)

    def test_reading_at_limit_decodes_on_its_own_range(self):
        _, resistance, _ = calibrate_gsr(np.array([683]))

        np.testing.assert_allclose(resistance, [40.2 * 4095 / 3], rtol=1e-12)

    def test_auto_range_applies_only_lowest_limit(self):
        # Range 1 at full scale is 287 kOhm / 5, below the lower limit of range 1.
        # In auto range the device can report such a reading as it switches range,
        # and only the lowest resistance that any range can measure applies.
        _, resistance, _ = calibrate_gsr(np.array([(1 << 14) | 4095]))

        np.testing.assert_allclose(resistance, [57.4], rtol=1e-12)

    def test_fixed_range_uses_configured_range(self):
        # The range bits are ignored in favour of the configured range
        raw = np.array([(3 << 14) | 2048])

        gsr_range, resistance, _ = calibrate_gsr(raw, range_setting=2)

        assert gsr_range[0] == 2
        np.testing.assert_allclose(
            resistance, [1000.0 / (2048 * 6 / 4095 - 1)], rtol=1e-12
        )

    def test_fixed_range_clamps_to_its_range(self):
        # Full scale lies below the range, an open circuit above it
        _, resistance, _ = calibrate_gsr(np.array([4095, 0]), range_setting=1)

        np.testing.assert_equal(resistance, np.array([63.0, 220.0]))

    def test_invalid_range_setting(self):
        with pytest.raises(ValueError):
            calibrate_gsr(np.array([697]), range_setting=5)

    def test_resistance_and_conductance_are_reciprocal(self):
        _, resistance, conductance = calibrate_gsr(self.RAW)

        np.testing.assert_allclose(conductance, 1000.0 / resistance)
