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

import struct
from io import SEEK_SET, SEEK_CUR
from queue import Queue
from typing import BinaryIO

import numpy as np


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


def flatten_list(lst: list | tuple) -> list:
    """Flatten the supplied list by one level

    Assumes that the supplied argument consists of lists itself. All elements are taken
    from the sublists and added to a fresh copy.

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
    return " ".join("{:02x}".format(i) for i in val)


def unpack(args: list | tuple) -> list | tuple | any:
    """Extract the first object if the list has length 1

    If the supplied list or tuple only features a single element, the element is
    retrieved and returned. If the list or tuple is longer, the entire list or tuple is
    returned.

    :param args: The list or tuple to unpack
    :return: The list or tuple itself or the single element if the argument has a
        length of 1
    """
    if len(args) == 1:
        return args[0]
    return args


#: Width of the packet timestamp counter used by current Shimmer firmware.
TIMESTAMP_MODULO_3_BYTE = 2**24

#: How close to the top of its range the previous sample must have been for a drop to
#: exactly zero to be a genuine overflow rather than an invalid record. One second at
#: the 32768 Hz device clock.
TIMESTAMP_WRAP_WINDOW = 32768

#: Sample periods a packet may lag its predecessor and still be read as reordered
#: rather than as an overflow.
TIMESTAMP_REORDER_PERIODS = 8

#: The reorder window is never allowed past this fraction of the modulo.
TIMESTAMP_MAX_WINDOW_DIVISOR = 8


def reorder_window_ticks(period_ticks: float | None, modulo: int) -> float:
    """How far back a sample may be and still be read as a reordered packet

    Sized in sample periods, because that is what tells the two cases apart: a reorder
    swaps packets that are adjacent in time - a handful of periods - whereas a dropout
    spanning the counter's overflow point is most of a modulo. Sizing the window as a
    fraction of the modulo confuses them: at ``modulo / 8`` on the 2-byte counter every
    dropout between 1.75 and 2.0 seconds reads as a reorder and the overflow is
    silently lost, and a 1.75 second gap is ordinary. Eight periods shrinks the band in
    which that can happen to about 16 milliseconds.

    Returns zero - the branch disabled - when the period is not known. Never guess: an
    infinite window would classify every backward step as a reorder and lose every
    overflow, which is worse than no reorder detection at all.

    :param period_ticks: Device ticks between consecutive samples, or None if unknown.
        For a binary recording this is the sampling-rate divider from the file header,
        which is that count directly.
    :param modulo: The counter's modulo, i.e. one above its largest value
    :return: The window in ticks, clamped so it can never reach the modulo and leave no
        backward step large enough to be read as an overflow
    """
    if period_ticks is None or period_ticks <= 0:
        return 0.0
    window = TIMESTAMP_REORDER_PERIODS * float(period_ticks)
    return min(window, modulo / TIMESTAMP_MAX_WINDOW_DIVISOR)


def find_invalid_timestamps(
    x: np.ndarray, modulo: int, reorder_window: float = 0.0
) -> np.ndarray:
    """Find timestamps that are zero without the counter having reached its origin

    Shimmer firmware stamps a packet when the sample tick starts it and does not write
    out a packet it never stamped, so a timestamp field of exactly zero marks an
    invalid record rather than a counter origin. LogAndStream v1.00.x-v1.01.003 could
    produce one under SD write back-pressure.

    Such a record matters far beyond itself: read as an overflow by :func:`unwrap`, it
    adds a whole modulo - 512 seconds for the 3-byte counter - to every later sample.

    The test is deliberately narrow, so that a genuine overflow onto zero is still
    recognised: the previous sample must be more than :data:`TIMESTAMP_WRAP_WINDOW`
    below the top of the range, where no real overflow could have come from. Counters
    narrower than 3 bytes are never flagged - their whole range is 2 seconds, so a
    stall really can cross one. A zero close enough to the origin to be a reordered
    packet is left to :func:`unwrap` to place, which is why the window is taken here
    too: reorder is tested before invalidity, and a zero can be either.

    The predecessor is the last **non-zero** sample, so a run of consecutive zeros is
    judged against the last record that carried a timestamp rather than against the
    zero before it.

    :param x: The raw timestamp array, with shape (N, )
    :param modulo: The counter's modulo, i.e. one above its largest value
    :param reorder_window: From :func:`reorder_window_ticks`; zero disables reorder
        detection, which is the safe default when the sampling rate is unknown
    :return: A boolean array of shape (N, ), True where the entry is invalid
    """
    invalid = np.zeros(len(x), dtype=bool)

    if modulo != TIMESTAMP_MODULO_3_BYTE or len(x) < 2:
        return invalid

    x = np.asarray(x, dtype=np.int64)
    is_zero = x == 0

    # Index of the last non-zero sample at or before each position. -1 where there has
    # not been one yet, which is the case a leading zero falls into.
    idx = np.arange(len(x))
    last_nonzero = np.maximum.accumulate(np.where(is_zero, -1, idx))

    # The first sample has nothing before it to contradict a zero, so start at 1.
    pred_idx = last_nonzero[:-1]
    has_pred = pred_idx >= 0
    pred = x[np.where(has_pred, pred_idx, 0)]

    invalid[1:] = (
        is_zero[1:]
        & has_pred
        & (pred > reorder_window)
        & (pred < modulo - TIMESTAMP_WRAP_WINDOW)
    )
    return invalid


def unwrap(
    x: np.ndarray,
    shift: int,
    invalid: np.ndarray | None = None,
    reorder_window: float = 0.0,
) -> np.ndarray:
    """Detect overflows in the data and unwrap them

    Each sample is classified by its **modular forward distance** from the one before
    it, with forward motion as the default:

    * a repeat of the previous value holds the timeline where it is;
    * a sample no further back than ``reorder_window`` is a reordered packet, and is
      placed where it was taken - below its predecessor, so the output is deliberately
      not monotonic;
    * anything else is forward motion, which is an overflow when the raw value fell.

    Comparing modular distances rather than unwrapped values is what lets a packet
    arriving late from *before* an overflow boundary be recognised. Compared as
    unwrapped values it looks like forward motion of nearly a whole modulo, so it is
    accepted and the next real sample is then read as a second overflow - two modulos
    from one out-of-order packet.

    Unlike earlier versions this does not modify ``x`` in place.

    :param x: The array to unwrap
    :param shift: The counter's modulo - the value a genuine overflow costs
    :param invalid: An optional boolean mask of shape (N, ). Entries marked True take
        no part in the unwrapping and carry the previous sample's value; see
        :func:`find_invalid_timestamps` for why that distinction is worth a whole
        modulo.
    :param reorder_window: From :func:`reorder_window_ticks`; zero disables reorder
        detection, leaving every backward step an overflow as before
    :return: An array of equal length that has been unwrapped
    """
    x = np.asarray(x, dtype=np.int64)
    if len(x) == 0:
        return x.copy()

    if invalid is None:
        invalid = np.zeros(len(x), dtype=bool)
    valid = ~invalid
    if not valid.any():
        return x.copy()

    xv = x[valid]

    # Forward distance in the counter's own arithmetic, so a step across the overflow
    # boundary is small in either direction rather than nearly a modulo. A negative
    # difference has one modulo added rather than being reduced outright, which is what
    # the other Shimmer host APIs do and what leaves a value at or above the modulo -
    # not something a real counter emits, but something a caller can pass - as plain
    # forward motion.
    diff = np.diff(xv)
    forward = np.where(diff < 0, diff + shift, diff)
    backwards = shift - forward

    # backwards > 0 excludes that out-of-range case, where it would otherwise be zero
    # and read as a reorder of no distance at all. For an in-range counter it is always
    # true and changes nothing.
    is_reorder = (backwards > 0) & (backwards <= reorder_window)
    step = np.where(forward == 0, 0, np.where(is_reorder, -backwards, forward))
    uv = xv[0] + np.concatenate(([0], np.cumsum(step)))

    out = np.empty(len(x), dtype=np.int64)
    out[valid] = uv
    if invalid.any():
        # An invalid record carries the value the timeline held when it arrived. Its
        # own timestamp means nothing, and the caller is expected to drop it; giving it
        # the held value keeps the series usable for anyone who does not.
        held = np.maximum.accumulate(np.where(valid, np.arange(len(x)), -1))
        first_valid = int(np.argmax(valid))
        out[invalid] = np.where(
            held[invalid] >= 0,
            out[np.where(held >= 0, held, first_valid)][invalid],
            uv[0],
        )
    return out


def resp_code_to_bytes(code: int | bytes | tuple[int, ...]) -> bytes:
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
    return (uncalibratedData - offset) * ((vRefP / gain) / 4095)


def battery_voltage_to_percent(battery_voltage):
    """Convert battery voltage to percent

    :param battery_voltage: Battery voltage in Volt
    :return: approximated battery state in percent based on manual
    """
    # reference values from: https://shimmersensing.com/wp-content/docs/support/documentation/Shimmer_User_Manual_rev3p.pdf (Page 53)
    reference_data_voltages = [
        3.2,
        3.627,
        3.645,
        3.663,
        3.681,
        3.699,
        3.717,
        3.7314,
        3.735,
        3.7386,
        3.7566,
        3.771,
        3.789,
        3.8034,
        3.8106,
        3.8394,
        3.861,
        3.8826,
        3.9078,
        3.933,
        3.969,
        4.0086,
        4.041,
        4.0734,
        4.113,
        4.167,
    ]
    reference_data_percentages = [
        0,
        5.9,
        9.8,
        13.8,
        17.7,
        21.6,
        25.6,
        29.5,
        33.4,
        37.4,
        41.3,
        45.2,
        49.2,
        53.1,
        57,
        61,
        64.9,
        68.9,
        72.8,
        76.7,
        80.7,
        84.6,
        88.5,
        92.5,
        96.4,
        100,
    ]

    battery_percent = np.interp(
        battery_voltage, reference_data_voltages, reference_data_percentages
    )

    battery_percent = min(battery_percent, 100)
    battery_percent = max(battery_percent, 0)

    return battery_percent


class PeekQueue(Queue):
    """A thread-safe queue implementation that allows peeking at the first element in
    the queue.

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
            raise ValueError("IO object must be seekable")

        self._fp = fp

    def _tell(self) -> int:
        return self._fp.tell()

    def _read(self, s: int) -> bytes:
        r = self._fp.read(s)
        if len(r) < s:
            raise IOError("Read beyond EOF")

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
