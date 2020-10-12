from serial import Serial

from pyshimmer.bluetooth.bt_const import INSTREAM_CMD_RESPONSE, ACK_COMMAND_PROCESSED
from pyshimmer.serial_base import SerialBase


class BluetoothSerial(SerialBase):

    def __init__(self, serial: Serial):
        super().__init__(serial)

    def read_varlen(self) -> bytes:
        arg_len = self.read_byte()
        arg = self.read(arg_len)
        return arg

    def write_varlen(self, arg: bytes) -> None:
        arg_len = len(arg)
        if arg_len > 255:
            raise ValueError(f'Variable-length argument is too long: {arg_len:d}')

        self.write_byte(arg_len)
        self.write(arg)

    def write_command(self, ccode: int, arg_format: str = None, *args) -> None:
        self.write_byte(ccode)

        if arg_format is not None:
            if arg_format == "varlen":
                self.write_varlen(args[0])
            else:
                self.write_packed(arg_format, *args)

    def read_ack(self) -> None:
        r = self.read_byte()
        if r != ACK_COMMAND_PROCESSED:
            raise ValueError('Byte received is no acknowledgment')

    def read_response(self, rcode: int, arg_format: str = None, instream: bool = False) -> any:
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
        return []
