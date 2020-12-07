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
from io import RawIOBase
from typing import Callable

from serial import Serial

from pyshimmer.util import unpack


class ReadAbort(Exception):
    """
    Raised by ShimmerSerial when a read operation was cancelled by the user.
    """
    pass


class BufferedReader:
    """
    Wraps around a RawIOBase object to enable buffered reads and peeks while only requesting as many bytes as needed
    for the current request from the underlying stream.

    :param io_obj: The binary stream from which to read data
    """

    def __init__(self, io_obj: RawIOBase):
        self._io_obj = io_obj
        self._buf = bytearray()

    def _do_read_or_throw(self, read_len: int) -> bytes:
        result = self._io_obj.read(read_len)
        if len(result) < read_len:
            raise ReadAbort('Read operation returned prematurely. Read was cancelled.')
        return result

    def _fill_buffer(self, n: int) -> None:
        avail = len(self._buf)
        needed = n - avail

        if needed > 0:
            self._buf += self._do_read_or_throw(needed)

    def _get_from_buf(self, n: int) -> bytes:
        self._fill_buffer(n)
        return bytes(self._buf[:n])

    def _take_from_buf(self, n: int) -> bytes:
        data = self._get_from_buf(n)
        self._buf = self._buf[n:]
        return data

    def read(self, n: int) -> bytes:
        """Read n bytes from the underlying stream

        :param n: The number of bytes to read
        :raises ReadAbort: If the read operation on the underlying object has been cancelled and the stream returns
            less bytes than requested.
        :return: The requested bytes
        """
        return self._take_from_buf(n)

    def peek(self, n: int) -> bytes:
        """Peek n bytes into the stream, but do not discard the data

        Takes n bytes from the stream and returns them but also keeps them in an internal buffer, such that they
        can be returned by a later call to :meth:`read`.

        :param n: The number of bytes to peek
        :raises ReadAbort: If the read operation on the underlying object has been cancelled and the stream returns
            less bytes than requested.
        :return: The requested bytes
        """
        return self._get_from_buf(n)

    def reset(self) -> None:
        """Clear the internal buffer of the reader

        """
        self._buf = bytearray()


class SerialBase:
    """Wrapper around :class:`serial.Serial` which provides multiple convenience methods.

    :param serial: The serial instance to wrap
    """

    def __init__(self, serial: Serial):
        if serial.timeout is not None:
            print('Warning: Serial Read timeout != None. This will interfere with the detection cancelled reads.')

        self._serial = serial
        self._reader = BufferedReader(serial)

    @staticmethod
    def _retrieve_packed(fn_read: Callable[[int], bytes], rformat: str) -> any:
        read_len = struct.calcsize(rformat)

        r = fn_read(read_len)
        args_unpacked = struct.unpack(rformat, r)
        return unpack(args_unpacked)

    def flush_input_buffer(self):
        """Flush the input buffer and remove any data that has been received but not yet read

        """
        self._serial.reset_input_buffer()
        self._reader.reset()

    def write(self, data: bytes) -> int:
        """Write the data to the underlying serial stream

        The call blocks until the data has been written.

        :param data: The data to write
        :return: The number of bytes written, is equal to the length of data
        """
        return self._serial.write(data)

    def write_byte(self, arg: int) -> int:
        """Write a single byte to the stream

        :param arg: The byte to write
        :return: The number of bytes written
        """
        return self.write_packed('B', arg)

    def write_packed(self, wformat: str, *args) -> int:
        """Pack a number of arguments using :mod:`struct` and write them to the stream

        :param wformat: The format to use, see :func:`struct.pack`
        :param args: The arguments for the format string
        :return: The number of bytes written to the stream
        """
        args_packed = struct.pack(wformat, *args)
        return self.write(args_packed)

    def read(self, read_len: int) -> bytes:
        """Read the requested number of bytes from the stream

         The call blocks until sufficient data is available.

        :param read_len: The number of bytes to read
        :return: The data as bytes instance
        """
        return self._reader.read(read_len)

    def read_packed(self, rformat: str) -> any:
        """Read the data requested by the format string and unpack it

        The function evaluates the :mod:`struct` format string, reads the required number of bytes, and returns the
        unpacked arguments.

        :param rformat: The string format
        :return: A variable number of arguments, depending on the format string
        """
        return self._retrieve_packed(self.read, rformat)

    def read_byte(self) -> int:
        """Read a single byte from the stream

        :return: The byte that was read
        """
        r = self.read_packed('B')
        return r

    def cancel_read(self) -> None:
        """Cancel ongoing read operation

        If another thread is blocked in a read operation, cancel the operation by calling this method.
        """
        self._serial.cancel_read()

    def peek(self, n: int) -> bytes:
        """Peek the requested number of bytes into the stream

        :param n: The number of bytes to return
        :return: The requested bytes
        """
        return self._reader.peek(n)

    def peek_packed(self, rformat: str) -> any:
        """Peek into the stream and return the requested packed arguments

        :param rformat: The format of the data to peek
        :return: The peeked data, can be a variable number of arguments, depending on the format string
        """
        return self._retrieve_packed(self.peek, rformat)

    def close(self) -> None:
        """Close the underlying serial stream

        """
        self._serial.close()
