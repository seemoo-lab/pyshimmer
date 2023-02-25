# pyshimmer - API for Shimmer sensor devices
# Copyright (C) 2023  Lukas Magel

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
from typing import Union, overload

import numpy as np

# Device clock rate in ticks per second
DEV_CLOCK_RATE: float = 32768.0

DEFAULT_BAUDRATE = 115200


def sr2dr(sr: float) -> int:
    """Calculate equivalent device-specific rate for a sample rate in Hz

    Device-specific sample rates are given in absolute clock ticks per unit of time. This function can be used to
    calculate such a rate for the Shimmer3.

    Args:
        sr(float): The sampling rate in Hz

    Returns:
        An integer which represents the equivalent device-specific sampling rate
    """
    dr_dec = DEV_CLOCK_RATE / sr
    return round(dr_dec)


def dr2sr(dr: int):
    """Calculate equivalent sampling rate for a given device-specific rate

    Device-specific sample rates are given in absolute clock ticks per unit of time. This function can be used to
    calculate a regular sampling rate in Hz from such a rate.

    Args:
        dr(int): The absolute device rate as int

    Returns:
        A floating-point number that represents the sampling rate in Hz
    """
    return DEV_CLOCK_RATE / dr


@overload
def sec2ticks(t_sec: float) -> int: ...


@overload
def sec2ticks(t_sec: np.ndarray) -> np.ndarray: ...


def sec2ticks(t_sec: Union[float, np.ndarray]) -> Union[int, np.ndarray]:
    """Calculate equivalent device clock ticks for a time in seconds

    Args:
        t_sec: A time in seconds
    Returns:
        An integer which represents the equivalent number of clock ticks
    """
    return round(t_sec * DEV_CLOCK_RATE)


@overload
def ticks2sec(t_ticks: int) -> float: ...


@overload
def ticks2sec(t_ticks: np.ndarray) -> np.ndarray: ...


def ticks2sec(t_ticks: Union[int, np.ndarray]) -> Union[float, np.ndarray]:
    """Calculate the time in seconds equivalent to a device clock ticks count

    Args:
        t_ticks: A clock tick counter for which to calculate the time in seconds
    Returns:
        A floating point time in seconds that is equivalent to the number of clock ticks
    """
    return t_ticks / DEV_CLOCK_RATE
