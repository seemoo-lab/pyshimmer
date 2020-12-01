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
import binascii
import struct

from serial import Serial

from pyshimmer.serial_base import SerialBase
from pyshimmer.uart.dock_const import CRC_INIT


def generate_crc(msg: bytes, crc_init: int) -> bytes:
    if len(msg) % 2 != 0:
        msg += b'\x00'

    crc = binascii.crc_hqx(msg, crc_init)
    crc_bin = struct.pack('<H', crc)
    return crc_bin


class DockSerial(SerialBase):

    def __init__(self, serial: Serial, crc_init: int = CRC_INIT):
        super().__init__(serial)
        self._crc_init = crc_init

        self._record_read = False
        self._read_crc_buf = bytearray()

        self._record_write = False
        self._write_crc_buf = bytearray()

    def _create_crc(self, msg: bytes) -> bytes:
        return generate_crc(msg, self._crc_init)

    def read(self, read_len: int) -> bytes:
        data = super().read(read_len)

        if self._record_read:
            self._read_crc_buf += data

        return data

    def write(self, data: bytes) -> int:
        if self._record_write:
            self._write_crc_buf += data

        return super().write(data)

    def start_read_crc_verify(self) -> None:
        self._record_read = True
        self._read_crc_buf = bytearray()

    def end_read_crc_verify(self) -> None:
        self._record_read = False

        exp_crc = self._create_crc(self._read_crc_buf)
        act_crc = super().read(len(exp_crc))
        if not exp_crc == act_crc:
            raise IOError('CRC check failed: Received data is invalid')

    def start_write_crc(self) -> None:
        self._record_write = True
        self._write_crc_buf = bytearray()

    def end_write_crc(self) -> None:
        self._record_write = False

        crc = self._create_crc(self._write_crc_buf)
        super().write(crc)
