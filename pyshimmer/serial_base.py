import struct

from serial import Serial

from pyshimmer.util import unpack


class ReadAbort(Exception):
    """
    Raised by ShimmerSerial when a read operation was cancelled.
    """
    pass


class SerialBase:

    def __init__(self, serial: Serial):
        if serial.timeout is not None:
            print('Warning: Serial Read timeout != None. This will interfere with the detection cancelled reads.')

        self._serial = serial
        self._peek_byte = None

    def _do_read_or_throw(self, read_len: int) -> bytes:
        result = self._serial.read(read_len)
        if len(result) < read_len:
            raise ReadAbort('Read operation returned prematurely. Read was cancelled.')
        return result

    def flush_input_buffer(self):
        self._serial.reset_input_buffer()
        self._peek_byte = None

    def write(self, data: bytes) -> int:
        return self._serial.write(data)

    def read(self, read_len: int) -> bytes:
        if read_len <= 0:
            return b''

        if self._peek_byte is not None:
            result = self._peek_byte
            self._peek_byte = None
            read_len -= 1
        else:
            result = b''

        result += self._do_read_or_throw(read_len)
        return result

    def cancel_read(self) -> None:
        self._serial.cancel_read()

    def peek(self) -> int:
        if self._peek_byte is None:
            self._peek_byte = self._do_read_or_throw(1)

        ret_values = struct.unpack('B', self._peek_byte)
        return ret_values[0]

    def write_packed(self, wformat: str, *args) -> int:
        args_packed = struct.pack(wformat, *args)
        return self.write(args_packed)

    def read_packed(self, rformat: str) -> any:
        read_len = struct.calcsize(rformat)

        r = self.read(read_len)
        args_unpacked = struct.unpack(rformat, r)
        return unpack(args_unpacked)

    def write_byte(self, arg: int) -> int:
        return self.write_packed('B', arg)

    def read_byte(self) -> int:
        r = self.read_packed('B')
        return r

    def close(self) -> None:
        self._serial.close()
