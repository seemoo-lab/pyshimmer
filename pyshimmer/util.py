import struct
from io import SEEK_SET, SEEK_CUR
from typing import BinaryIO

import numpy as np


def bit_is_set(bitfield, mask):
    return bitfield & mask == mask


def raise_to_next_pow(x):
    if x <= 0:
        return 1

    return 1 << (x - 1).bit_length()


def flatten_list(lst):
    lst_flat = [val for sublist in lst for val in sublist]
    return lst_flat


def fmt_hex(val_bin):
    return ' '.join('{:02x}'.format(i) for i in val_bin)


def unpack(args):
    if len(args) == 1:
        return args[0]
    return args


def unwrap(x, shift):
    """Detect overflows in the data and unwrap them

    The function tries to detect overflows in the input array x, with shape (N, ). It is assumed that x is monotonically
    increasing everywhere but at the overflows. An overflow occurs if for two consecutive points x_i and x_i+1 in the
    series x_i > x_i+1. For every such point, the function will add the value of the shift parameter to all following
    samples, i.e. x_k' = x_k + shift, for every k > i.

    Args:
        x: The array to unwrap
        shift: The value which to add to the series after each overflow point

    Returns:
        An array of equal length that has been unwrapped

    """
    x_diff = np.diff(x)
    wrap_points = np.argwhere(x_diff < 0)

    for i in wrap_points.flatten():
        x += (np.arange(len(x)) > i) * shift

    return x


class FileIOBase:

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
