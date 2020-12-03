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
import os
import pty
from io import BytesIO, RawIOBase, SEEK_END, SEEK_SET
from typing import Optional, Union, Tuple, BinaryIO

from serial import Serial


class MockSerial(RawIOBase):

    def __init__(self, timeout=None):
        self._read_buf = BytesIO()
        self._write_buf = BytesIO()

        self.timeout = timeout

        self.test_closed = False
        self.test_input_flushed = False
        self.test_read_cancelled = False

    def readable(self) -> bool:
        return True

    def writable(self) -> bool:
        return True

    def close(self) -> None:
        super().close()

        self.test_closed = True

    def readinto(self, b: bytearray) -> Optional[int]:
        return self._read_buf.readinto(b)

    def write(self, b: Union[bytes, bytearray]) -> Optional[int]:
        return self._write_buf.write(b)

    def reset_input_buffer(self):
        self.test_input_flushed = True

        self._read_buf.seek(0, SEEK_END)

    def cancel_read(self):
        self.test_read_cancelled = True

    def test_put_read_data(self, data: bytes) -> None:
        cur_pos = self._read_buf.tell()

        self._read_buf.seek(0, SEEK_END)
        self._read_buf.write(data)
        self._read_buf.seek(cur_pos, SEEK_SET)

    def test_get_remaining_read_data(self) -> bytes:
        return self._read_buf.read()

    def test_clear_read_buffer(self) -> None:
        self._read_buf = BytesIO()

    def test_get_write_data(self) -> bytes:
        self._write_buf.seek(0, SEEK_SET)
        data = self._write_buf.read()

        self._write_buf = BytesIO()
        return data


class PTYSerialMockCreator:

    def __init__(self):
        self._master_fobj = None
        self._slave_fobj = None

        self._slave_serial = None

    @staticmethod
    def _create_fobj(fd: int) -> BinaryIO:
        # https://bugs.python.org/issue20074
        fobj = os.fdopen(fd, 'r+b', 0)
        assert fobj.fileno() == fd

        return fobj

    def create_mock(self) -> Tuple[Serial, BinaryIO]:
        master_fd, slave_fd = pty.openpty()

        self._master_fobj = self._create_fobj(master_fd)
        self._slave_fobj = self._create_fobj(slave_fd)

        # Serial Baud rate is ignored by the driver and can be set to any value
        slave_path = os.ttyname(slave_fd)
        self._slave_serial = Serial(slave_path, 115200)

        return self._slave_serial, self._master_fobj

    def close(self):
        self._slave_serial.close()

        self._master_fobj.close()
        self._slave_fobj.close()
