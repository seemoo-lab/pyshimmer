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
"""Conversion of the galvanic skin response channel

The GSR circuit measures the resistance between two electrodes by comparing it
against one of four reference resistors. The device selects the reference resistor
automatically and reports the selected range together with the measurement in a
single channel value.
"""

from __future__ import annotations

import numpy as np

# Number of bits of the raw reading. The two remaining bits of the channel value
# encode the active range.
GSR_ADC_BITS = 14
GSR_ADC_MASK = (1 << GSR_ADC_BITS) - 1

# The reference resistor of the amplifier for each of the four ranges
GSR_REF_RESISTORS_KOHM = np.array([40.2, 287.0, 1000.0, 3300.0])

# The resistance range that each setting is able to measure. A measurement below the
# lower limit of its range is not meaningful and is reported as the limit itself.
GSR_MIN_RESISTANCE_KOHM = np.array([8.0, 63.0, 220.0, 680.0])
GSR_MAX_RESISTANCE_KOHM = np.array([63.0, 220.0, 680.0, 4700.0])

# Properties of the microcontroller ADC to which the GSR circuit is connected
GSR_ADC_REF_VOLT = 3.0
GSR_ADC_MAX = 4095

# Reference voltage of the amplifier
GSR_AMPLIFIER_VOLT = 0.5


def split_gsr_raw(raw: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Split a raw GSR channel value into its range and its ADC reading

    :param raw: The raw values of the GSR channel
    :return: A tuple of the active range and the ADC reading
    """
    raw = np.asarray(raw).astype(np.int64)

    gsr_range = raw >> GSR_ADC_BITS
    adc_value = raw & GSR_ADC_MASK

    return gsr_range, adc_value


def calibrate_gsr(raw: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Convert the raw GSR channel into a skin resistance and conductance

    :param raw: The raw values of the GSR channel
    :return: A tuple of the active range, the skin resistance in kOhm, and the skin
        conductance in microsiemens
    """
    gsr_range, adc_value = split_gsr_raw(raw)

    volts = adc_value * GSR_ADC_REF_VOLT / GSR_ADC_MAX
    r_feedback = GSR_REF_RESISTORS_KOHM[gsr_range]

    with np.errstate(divide="ignore", invalid="ignore"):
        resistance = r_feedback / ((volts / GSR_AMPLIFIER_VOLT) - 1.0)

    # A reading at or below the lower limit of the active range yields a resistance
    # that is meaningless or even negative. The device reports the limit instead.
    resistance = np.maximum(resistance, GSR_MIN_RESISTANCE_KOHM[gsr_range])

    conductance = 1000.0 / resistance

    return gsr_range, resistance, conductance
