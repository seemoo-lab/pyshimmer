import binascii
import struct

from serial import Serial

from pyshimmer.serial_base import SerialBase
from pyshimmer.uart.dock_const import CRC_INIT


class DockSerial(SerialBase):

    def __init__(self, serial: Serial, crc_init: int = CRC_INIT):
        super().__init__(serial)
        self._crc_init = crc_init

        self._record_read = False
        self._read_crc_buf = bytearray()

        self._record_write = False
        self._write_crc_buf = bytearray()

    def _create_crc(self, msg: bytes) -> bytes:
        if len(msg) % 2 != 0:
            msg += b'\x00'

        crc = binascii.crc_hqx(msg, self._crc_init)
        crc_bin = struct.pack('<H', crc)
        return crc_bin

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
