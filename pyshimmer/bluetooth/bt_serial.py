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
from serial import Serial

from pyshimmer.bluetooth.bt_const import INSTREAM_CMD_RESPONSE, ACK_COMMAND_PROCESSED
from pyshimmer.serial_base import SerialBase


class BluetoothSerial(SerialBase):
    """Another wrapper layer around the Serial interface

    :arg serial: The :class:`serial.Serial` instance to wrap
    """

    def __init__(self, serial: Serial):
        super().__init__(serial)

    def read_varlen(self) -> bytes:
        """Read the number of bytes specified by the first byte read

        The function reads a single byte that it interprets as a length field with value L and then reads the
        specified number of L bytes from the stream.

        :return: A variable number of bytes
        """
        arg_len = self.read_byte()
        arg = self.read(arg_len)
        return arg

    def write_varlen(self, arg: bytes) -> None:
        """Write a variable number of bytes by prepending the data with their length

        The function first writes the length of the data as a single byte, then writes the data itself.

        :param arg: The data to write
        :raises ValueError: If the number of bytes exceeds the maximum length of 256
        """
        arg_len = len(arg)
        if arg_len > 255:
            raise ValueError(f'Variable-length argument is too long: {arg_len:d}')

        self.write_byte(arg_len)
        self.write(arg)

    def write_command(self, ccode: int, arg_format: str = None, *args) -> None:
        """Write a Bluetooth command to the stream

        :param ccode: The code of the command
        :param arg_format: The argument format, can be a :func:`struct.pack` string or `varlen` for a variable-length
            argument
        :param args: The arguments to write along with the command, must meet the requirements of the format string
        """
        self.write_byte(ccode)

        if arg_format is not None:
            if arg_format == "varlen":
                self.write_varlen(args[0])
            else:
                self.write_packed(arg_format, *args)

    def read_ack(self) -> None:
        """Read and assert that the next byte in the stream is an acknowledgment

        :raises ValueError: If the byte is not an acknowledgment

        """
        r = self.read_byte()
        if r != ACK_COMMAND_PROCESSED:
            raise ValueError('Byte received is no acknowledgment')

    def read_response(self, rcode: int, arg_format: str = None, instream: bool = False) -> any:
        """Read a Bluetooth command response from the stream

        :param rcode: The expected response code
        :param arg_format: The format string to use when decoding the response arguments. Can be None, a
            :func:`struct.unpack` string or `varlen`. If None, no arguments will be read.
        :param instream: If the response is an in-stream response. If true, the first byte is expected to be the
            in-stream flag byte.
        :raises RuntimeError: If the response code is incorrect
        :return: The arguments of the response or () if the response has no arguments
        """
        if instream:
            first_byte = self.read_byte()
            if first_byte != INSTREAM_CMD_RESPONSE:
                raise RuntimeError(f'Received incorrect instream response code: 0x{first_byte:x}')

        actual_rcode = self.read_byte()
        if rcode != actual_rcode:
            raise RuntimeError(f'Received incorrect response code: 0x{rcode:x} != 0x{actual_rcode:x}')

        if arg_format is not None:
            if arg_format == "varlen":
                return self.read_varlen()
            else:
                return self.read_packed(arg_format)
        return ()
