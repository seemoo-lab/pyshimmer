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
from io import BytesIO, RawIOBase, SEEK_END, SEEK_SET
from typing import Optional, Union


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

    def test_clear_read_buffer(self) -> None:
        self._read_buf = BytesIO()

    def test_get_write_data(self) -> bytes:
        self._write_buf.seek(0, SEEK_SET)
        data = self._write_buf.read()

        self._write_buf = BytesIO()
        return data
