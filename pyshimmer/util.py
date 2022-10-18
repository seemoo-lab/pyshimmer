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
import struct
from io import SEEK_SET, SEEK_CUR
from queue import Queue
from typing import BinaryIO, Tuple, Union, List

import numpy as np
import math


def bit_is_set(bitfield: int, mask: int) -> bool:
    """Check if the bit set in the mask is also set in the bitfield

    :param bitfield: The bitfield stored as an integer of arbitrary length
    :param mask: The mask where only a single bit is set
    :return: True if the bit in the mask is set in the bitfield, else False
    """
    return bitfield & mask == mask


def raise_to_next_pow(x: int) -> int:
    """Raise the argument to the next power of 2

    Example:
        - 1 --> 1
        - 2 --> 2
        - 3 --> 4
        - 5 --> 8

    :param x: The value to raise to the next power
    :return: The raised value
    """
    if x <= 0:
        return 1

    return 1 << (x - 1).bit_length()


def flatten_list(lst: Union[List, Tuple]) -> List:
    """Flatten the supplied list by one level

    Assumes that the supplied argument consists of lists itself. All elements are taken from the sublists and added
    to a fresh copy.

    :param lst: A list of lists
    :return: A list with the contents of the sublists
    """
    lst_flat = [val for sublist in lst for val in sublist]
    return lst_flat


def fmt_hex(val: bytes) -> str:
    """Format the supplied array of bytes as str

    :param val: The binary array to format
    :return: The resulting string
    """
    return ' '.join('{:02x}'.format(i) for i in val)


def unpack(args: Union[List, Tuple]) -> Union[List, Tuple, any]:
    """Extract the first object if the list has length 1

    If the supplied list or tuple only features a single element, the element is retrieved and returned. If the list or
    tuple is longer, the entire list or tuple is returned.

    :param args: The list or tuple to unpack
    :return: The list or tuple itself or the single element if the argument has a length of 1
    """
    if len(args) == 1:
        return args[0]
    return args


def unwrap(x: np.ndarray, shift: int) -> np.ndarray:
    """Detect overflows in the data and unwrap them

    The function tries to detect overflows in the input array x, with shape (N, ). It is assumed that x is monotonically
    increasing everywhere but at the overflows. An overflow occurs if for two consecutive points x_i and x_i+1 in the
    series x_i > x_i+1. For every such point, the function will add the value of the shift parameter to all following
    samples, i.e. x_k' = x_k + shift, for every k > i.

    :param x: The array to unwrap
    :param shift: The value which to add to the series after each overflow point
    :return: An array of equal length that has been unwrapped
    """
    x_diff = np.diff(x)
    wrap_points = np.argwhere(x_diff < 0)

    for i in wrap_points.flatten():
        x += (np.arange(len(x)) > i) * shift

    return x


def resp_code_to_bytes(code: Union[int, Tuple[int, ...], bytes]) -> bytes:
    """Convert the supplied response code to bytes

    :param code: The code, can be an int, a tuple of ints, or bytes
    :return: The supplied code as byte array
    """
    if isinstance(code, int):
        code = (code,)
    if isinstance(code, tuple):
        code = bytes(code)

    return code


def calibrate_u12_adc_value(uncalibratedData, offset, vRefP, gain):
    """Convert the uncalibrated data to calibrated data

    :param uncalibratedData: Raw voltage measurement from device
    :param offset: Voltage offset in measured data
    :param vRefP: Voltage reference signal in Volt
    :param gain: gain factor
    :return: Calibrated voltage in Volt
    """
    return ((uncalibratedData - offset) * ((vRefP/gain)/4095))


def battery_voltage_to_percent(battery_voltage):
    """Convert battery voltage to percent

    :param battery_voltage: Battery voltage in Volt
    :return: approximated battery state in percent based on manual 
    """
    # reference values from: https://shimmersensing.com/wp-content/docs/support/documentation/Shimmer_User_Manual_rev3p.pdf (Page 53)
    reference_data_voltages = [3.2, 3.627, 3.645, 3.663, 3.681, 3.699, 3.717, 3.7314, 3.735, 3.7386, 3.7566, 3.771, 3.789, 3.8034, 3.8106, 3.8394, 3.861, \
        3.8826, 3.9078, 3.933, 3.969, 4.0086, 4.041, 4.0734, 4.113, 4.167]
    reference_data_percentages = [0, 5.9, 9.8, 13.8, 17.7, 21.6, 25.6, 29.5, 33.4, 37.4, 41.3, 45.2, 49.2, 53.1, 57, 61, 64.9, 68.9, 72.8, 76.7, 80.7, 84.6, \
        88.5, 92.5, 96.4, 100]

    battery_percent = np.interp(battery_voltage, reference_data_voltages, reference_data_percentages)

    battery_percent = min(battery_percent, 100)
    battery_percent = max(battery_percent, 0)

    return battery_percent


class PeekQueue(Queue):
    """A thread-safe queue implementation that allows peeking at the first element in the queue.

    Based on a suggestion on StackOverflow:
    https://stackoverflow.com/questions/1293966/best-way-to-obtain-indexed-access-to-a-python-queue-thread-safe
    """

    def peek(self):
        """Peek at the element that will be removed next.

        :return: The next entry in the queue to be removed or None if the queue is empty
        """
        # noinspection PyUnresolvedReferences
        with self.mutex:
            if self._qsize() > 0:
                return self.queue[0]

            return None


class FileIOBase:
    """Convenience wrapper around a BinaryIO file object

    Serves as an (abstract) base class for IO operations

    :arg fp: The file to wrap
    """

    def __init__(self, fp: BinaryIO):
        if not fp.seekable():
            raise ValueError('IO object must be seekable')

        self._fp = fp

    def _tell(self) -> int:
        return self._fp.tell()

    def _read(self, s: int) -> bytes:
        r = self._fp.read(s)
        if len(r) < s:
            raise IOError('Read beyond EOF')

        return r

    def _seek(self, off: int = 0) -> None:
        self._fp.seek(off, SEEK_SET)

    def _seek_relative(self, off: int = 0) -> None:
        self._fp.seek(off, SEEK_CUR)

    def _read_packed(self, fmt: str) -> any:
        s = struct.calcsize(fmt)
        val_bin = self._read(s)

        args = struct.unpack(fmt, val_bin)
        return unpack(args)
