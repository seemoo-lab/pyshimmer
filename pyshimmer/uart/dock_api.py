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
from typing import Tuple

from serial import Serial

from pyshimmer.dev.base import sec2ticks, ticks2sec
from pyshimmer.dev.exg import ExGRegister
from pyshimmer.dev.fw_version import get_firmware_type, EFirmwareType
from pyshimmer.uart.dock_const import *
from pyshimmer.uart.dock_serial import DockSerial
from pyshimmer.util import unpack


class ShimmerDock:
    """Main API to communicate with the Shimmer over the Dock UART

    :arg ser: The serial interface to use for communication

    """

    def __init__(self, ser: Serial, flush_before_req=True):
        self._serial = DockSerial(ser)
        self._flush_before_req = flush_before_req

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.close()

    def _read_resp_type_or_throw(self, expected: int) -> int:
        r = self._serial.read_byte()
        if r != START_CHAR:
            raise IOError(f'Unknown start character encountered: {r:x}')

        cmd = self._serial.read_byte()
        if cmd == UART_BAD_ARG_RESPONSE:
            raise IOError('Command failed: Bad argument')
        elif cmd == UART_BAD_CMD_RESPONSE:
            raise IOError('Command failed: Unknown command')
        elif cmd == UART_BAD_CRC_RESPONSE:
            raise IOError('Command failed: CRC Error')
        elif cmd != expected:
            raise IOError(f'Wrong response type: {expected:x} != {cmd:x}')

        return cmd

    def _write_packet(self, cmd: int, comp: int, prop: int, data: bytes = bytes()) -> None:
        if self._flush_before_req:
            self._serial.flush_input_buffer()
        self._serial.start_write_crc()

        pkt_len = 2 + len(data)
        self._serial.write_packed('<BBBBB', START_CHAR, cmd, pkt_len, comp, prop)
        self._serial.write(data)

        self._serial.end_write_crc()

    def _write_packet_wformat(self, cmd: int, comp: int, prop: int, fmt: str, *args: any) -> None:
        data = struct.pack(fmt, *args)
        self._write_packet(cmd, comp, prop, data)

    def _read_response(self) -> Tuple[int, int, bytes]:
        self._serial.start_read_crc_verify()

        self._read_resp_type_or_throw(UART_RESPONSE)
        pkt_len, comp, prop = self._serial.read_packed('BBB')

        data_len = pkt_len - 2
        data = self._serial.read(data_len)

        self._serial.end_read_crc_verify()
        return comp, prop, data

    def _read_response_verify(self, exp_comp: int, exp_prop: int) -> bytes:
        comp, prop, data = self._read_response()

        if exp_comp != comp:
            raise IOError(f'Encountered unexpected component type in response: {exp_comp:x} != {comp:x}')
        elif exp_prop != prop:
            raise IOError(f'Encountered unexpected property type in response: {exp_prop:x} != {prop:x}')

        return data

    def _read_response_wformat_verify(self, exp_comp: int, exp_prop: int, fmt: str) -> any:
        data_packed = self._read_response_verify(exp_comp, exp_prop)
        data = struct.unpack(fmt, data_packed)
        return unpack(data)

    def _read_ack(self) -> None:
        self._serial.start_read_crc_verify()
        self._read_resp_type_or_throw(UART_ACK_RESPONSE)
        self._serial.end_read_crc_verify()

    def close(self) -> None:
        """Close the underlying serial interface and release all resources

        """
        self._serial.close()

    def get_mac_address(self) -> Tuple[int, ...]:
        """Retrieve the Bluetooth MAC address of the device

        :return: A tuple containing six integer values, each representing a single byte of the address
        """
        self._write_packet(UART_GET, UART_COMP_SHIMMER, UART_PROP_MAC)

        mac = self._read_response_wformat_verify(UART_COMP_SHIMMER, UART_PROP_MAC, 'BBBBBB')
        return mac

    def set_rtc(self, ts_sec: float) -> None:
        """Set the real-time clock of the device

        Specify the UNIX timestamp in seconds as new value for the real-time clock of the device

        :param ts_sec: The UNIX timestamp in seconds
        """
        ticks = sec2ticks(ts_sec)
        self._write_packet_wformat(UART_SET, UART_COMP_SHIMMER, UART_PROP_RWC_CFG_TIME, '<Q', ticks)
        self._read_ack()

    def get_rtc(self) -> float:
        """Retrieve the current value of the real-time clock

        :return: A floating-point value representing the current value of the real-time clock as UNIX timestamp
            in seconds
        """
        self._write_packet(UART_GET, UART_COMP_SHIMMER, UART_PROP_CURR_LOCAL_TIME)
        ticks = self._read_response_wformat_verify(UART_COMP_SHIMMER, UART_PROP_CURR_LOCAL_TIME, '<Q')
        return ticks2sec(ticks)

    def get_config_rtc(self) -> float:
        """Get the value that was last set for the real-time clock

        Example:

            The real-time clock is set to a value of 42s. Subsequent calls to :meth:`get_rtc` will return v > 42s,
            while :meth:`get_config_rtc` will return 42s.

        :return: A floating-point value representing the last configured value for the real-time clock as UNIX
            timestamp in seconds
        """
        self._write_packet(UART_GET, UART_COMP_SHIMMER, UART_PROP_RWC_CFG_TIME)
        ticks = self._read_response_wformat_verify(UART_COMP_SHIMMER, UART_PROP_RWC_CFG_TIME, '<Q')
        return ticks2sec(ticks)

    def get_firmware_version(self) -> Tuple[int, EFirmwareType, int, int, int]:
        """Retrieve the firmware version of the device

        :return: A tuple containing the following values:
            - The hardware version, should be 3 for Shimmer3
            - The firmware type: LogAndStream or SDLog
            - The major release version
            - The minor release version
            - The patch level
        """
        self._write_packet(UART_GET, UART_COMP_SHIMMER, UART_PROP_VER)
        hw_ver, fw_type_bin, major, minor, rel = self._read_response_wformat_verify(UART_COMP_SHIMMER,
                                                                                    UART_PROP_VER, '<BHHBB')
        fw_type = get_firmware_type(fw_type_bin)
        return hw_ver, fw_type, major, minor, rel

    def get_firmware_type(self) -> EFirmwareType:
        """Retrieve the active firmware type

        :return: The firmware type: LogAndStream or SDLog
        """
        _, fw_type, _, _, _ = self.get_firmware_version()
        return fw_type

    def get_infomem(self, addr: int, dlen: int) -> bytes:
        """Access the infomem memory and retrieve the specified range

        :param addr: The start address
        :param dlen: The length of the memory block that will be retrieved
        :return: The bytes of the memory block
        """
        # Due to a bug in the firmware code, we must manually set a variable in the firmware to a specific value
        # using a different command before we can read the InfoMem.
        self._write_packet_wformat(UART_GET, UART_COMP_DAUGHTER_CARD, UART_PROP_CARD_ID, '<BH', 0x0, 0x0)
        self._read_response()

        self._write_packet_wformat(UART_GET, UART_COMP_SHIMMER, UART_PROP_INFOMEM, '<BH', dlen, addr)
        return self._read_response_verify(UART_COMP_SHIMMER, UART_PROP_INFOMEM)

    def get_exg_register(self, chip_id: int) -> ExGRegister:
        if not 0 <= chip_id <= 1:
            raise ValueError('Parameter chip_id must be 0 or 1')

        offset = UART_INFOMEM_EXG_OFFSET + chip_id * 0x0A
        dlen = 0x0A

        reg_data = self.get_infomem(offset, dlen)
        return ExGRegister(reg_data)
