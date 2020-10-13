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
from abc import ABC, abstractmethod
from typing import List

from pyshimmer.bluetooth.bt_const import *
from pyshimmer.bluetooth.bt_serial import BluetoothSerial
from pyshimmer.device import dr2sr, EChannelType, ChannelDataType, sec2ticks, ticks2sec, ExGRegister, \
    get_firmware_type
from pyshimmer.util import bit_is_set


class DataPacket:

    def __init__(self, stream_types):
        self._types = stream_types
        self._values = {}

    @property
    def channels(self) -> List[EChannelType]:
        return [t for t, _ in self._types]

    @property
    def channel_types(self) -> List[ChannelDataType]:
        return [t for _, t in self._types]

    def __getitem__(self, item: EChannelType) -> any:
        return self._values[item]

    def receive(self, ser: BluetoothSerial) -> None:
        ser.read_response(DATA_PACKET)

        for channel_type, channel_dtype in self._types:
            data_bin = ser.read(channel_dtype.size)
            self._values[channel_type] = channel_dtype.decode(data_bin)


class ShimmerCommand(ABC):

    @abstractmethod
    def send(self, ser: BluetoothSerial) -> None:
        pass

    def has_response(self) -> bool:
        return False

    def get_response_code(self) -> int:
        return 0

    def receive(self, ser: BluetoothSerial) -> any:
        return None


class ResponseCommand(ShimmerCommand, ABC):

    def __init__(self, rcode):
        self._rcode = rcode

    def has_response(self) -> bool:
        return True

    def get_response_code(self) -> int:
        return self._rcode


class OneShotCommand(ShimmerCommand):

    def __init__(self, cmd_code):
        self._code = cmd_code

    def send(self, ser: BluetoothSerial) -> None:
        ser.write_command(self._code)


class GetStringCommand(ResponseCommand):

    def __init__(self, req_code: int, resp_code: int, encoding: str = 'utf8'):
        super().__init__(resp_code)
        self._req_code = req_code
        self._encoding = encoding

    def send(self, ser: BluetoothSerial) -> None:
        ser.write_command(self._req_code)

    def receive(self, ser: BluetoothSerial) -> any:
        str_bin = ser.read_response(self._rcode, 'varlen')
        return str_bin.decode(self._encoding)


class SetStringCommand(ShimmerCommand):

    def __init__(self, req_code: int, str_data: str, encoding: str = 'utf8'):
        self._req_code = req_code
        self._str_data = str_data
        self._encoding = encoding

    def send(self, ser: BluetoothSerial) -> None:
        str_bin = self._str_data.encode(self._encoding)
        ser.write_command(self._req_code, 'varlen', str_bin)


class GetSamplingRateCommand(ResponseCommand):

    def __init__(self):
        super().__init__(SAMPLING_RATE_RESPONSE)

    def send(self, ser: BluetoothSerial) -> None:
        ser.write_command(GET_SAMPLING_RATE_COMMAND)

    def receive(self, ser: BluetoothSerial) -> None:
        sr_clock = ser.read_response(SAMPLING_RATE_RESPONSE, arg_format='<H')
        sr = dr2sr(sr_clock)
        return sr


class GetConfigTimeCommand(ResponseCommand):

    def __init__(self):
        super().__init__(CONFIGTIME_RESPONSE)

    def send(self, ser: BluetoothSerial) -> None:
        ser.write_command(GET_CONFIGTIME_COMMAND)

    def receive(self, ser: BluetoothSerial) -> any:
        r = ser.read_response(CONFIGTIME_RESPONSE, arg_format='varlen')
        return int(r)


class SetConfigTimeCommand(ShimmerCommand):

    def __init__(self, time_ut_ms):
        self._time = time_ut_ms

    def send(self, ser: BluetoothSerial) -> None:
        time_str = '{:d}'.format(int(self._time))
        time_bin = time_str.encode('ascii')

        ser.write_command(SET_CONFIGTIME_COMMAND, "varlen", time_bin)


class GetRealTimeClockCommand(ResponseCommand):

    def __init__(self):
        super().__init__(RWC_RESPONSE)

    def send(self, ser: BluetoothSerial) -> None:
        ser.write_command(GET_RWC_COMMAND)

    def receive(self, ser: BluetoothSerial) -> any:
        t_ticks = ser.read_response(RWC_RESPONSE, arg_format="<Q")
        return ticks2sec(t_ticks)


class SetRealTimeClockCommand(ShimmerCommand):

    def __init__(self, ts_sec: float):
        self._time = int(ts_sec)

    def send(self, ser: BluetoothSerial) -> None:
        t_ticks = sec2ticks(self._time)
        ser.write_command(SET_RWC_COMMAND, '<Q', t_ticks)


class GetStatusCommand(ResponseCommand):
    STATUS_DOCKED_BF = 1 << 0
    STATUS_SENSING_BF = 1 << 1
    STATUS_RTC_SET_BF = 1 << 2
    STATUS_LOGGING_BF = 1 << 3
    STATUS_STREAMING_BF = 1 << 4
    STATUS_SD_PRESENT_BF = 1 << 5
    STATUS_SD_ERROR_BF = 1 << 6
    STATUS_RED_LED_BF = 1 << 7
    STATUS_BITFIELDS = (STATUS_DOCKED_BF, STATUS_SENSING_BF, STATUS_RTC_SET_BF, STATUS_LOGGING_BF, STATUS_STREAMING_BF,
                        STATUS_SD_PRESENT_BF, STATUS_SD_ERROR_BF, STATUS_RED_LED_BF)

    def __init__(self):
        super().__init__(INSTREAM_CMD_RESPONSE)

    def unpack_status_bitfields(self, val):
        values = [bit_is_set(val, f) for f in self.STATUS_BITFIELDS]
        return values

    def send(self, ser: BluetoothSerial) -> None:
        ser.write_command(GET_STATUS_COMMAND)

    def receive(self, ser: BluetoothSerial) -> any:
        bitfields = ser.read_response(STATUS_RESPONSE, arg_format='B', instream=True)
        return self.unpack_status_bitfields(bitfields)


class GetFirmwareVersionCommand(ResponseCommand):

    def __init__(self):
        super().__init__(FW_VERSION_RESPONSE)

    def send(self, ser: BluetoothSerial) -> None:
        ser.write_command(GET_FW_VERSION_COMMAND)

    def receive(self, ser: BluetoothSerial) -> any:
        fw_type_bin, major, minor, rel = ser.read_response(FW_VERSION_RESPONSE, arg_format='<HHBB')
        fw_type = get_firmware_type(fw_type_bin)
        return fw_type, major, minor, rel


class InquiryCommand(ResponseCommand):

    def __init__(self):
        super().__init__(INQUIRY_RESPONSE)

    @staticmethod
    def decode_channel_types(ct_bin):
        ctypes_index = struct.unpack('B' * len(ct_bin), ct_bin)
        ctypes = [BtChannelsByIndex[i] for i in ctypes_index]
        return ctypes

    def send(self, ser: BluetoothSerial) -> None:
        ser.write_command(INQUIRY_COMMAND)

    def receive(self, ser: BluetoothSerial) -> any:
        sr_val, _, n_ch, buf_size = ser.read_response(INQUIRY_RESPONSE, arg_format='<HIBB')
        channel_conf = ser.read(n_ch)

        sr = dr2sr(sr_val)
        ctypes = self.decode_channel_types(channel_conf)

        return sr, buf_size, ctypes


class StartStreamingCommand(OneShotCommand):

    def __init__(self):
        super().__init__(START_STREAMING_COMMAND)


class StopStreamingCommand(OneShotCommand):

    def __init__(self):
        super().__init__(STOP_STREAMING_COMMAND)


class GetEXGRegsCommand(ResponseCommand):

    def __init__(self, chip_id):
        super().__init__(EXG_REGS_RESPONSE)

        self._chip = chip_id
        self._offset = 0x0
        self._rlen = 0xA

    def send(self, ser: BluetoothSerial) -> None:
        ser.write_command(GET_EXG_REGS_COMMAND, 'BBB', self._chip, self._offset, self._rlen)

    def receive(self, ser: BluetoothSerial) -> any:
        rlen = ser.read_response(EXG_REGS_RESPONSE, arg_format='B')
        if not rlen == self._rlen:
            raise ValueError('Response does not contain required amount of bytes')

        reg_data = ser.read(rlen)
        return ExGRegister(reg_data)


class SetEXGRegsCommand(ShimmerCommand):

    def __init__(self, chip_id, offset, data):
        self._chip = chip_id
        self._offset = offset
        self._data = data

    def send(self, ser: BluetoothSerial) -> None:
        dlen = len(self._data)
        ser.write_command(SET_EXG_REGS_COMMAND, 'BBB', self._chip, self._offset, dlen)
        ser.write(self._data)


class GetExperimentIDCommand(GetStringCommand):

    def __init__(self):
        super().__init__(GET_EXPID_COMMAND, EXPID_RESPONSE)


class SetExperimentIDCommand(SetStringCommand):

    def __init__(self, exp_id: str):
        super().__init__(SET_EXPID_COMMAND, exp_id)


class GetDeviceNameCommand(GetStringCommand):

    def __init__(self):
        super().__init__(GET_SHIMMERNAME_COMMAND, SHIMMERNAME_RESPONSE)


class SetDeviceNameCommand(SetStringCommand):

    def __init__(self, dev_name: str):
        super().__init__(SET_SHIMMERNAME_COMMAND, dev_name)


class StartLoggingCommand(OneShotCommand):

    def __init__(self):
        super().__init__(START_LOGGING_COMMAND)


class StopLoggingCommand(OneShotCommand):

    def __init__(self):
        super().__init__(STOP_LOGGING_COMMAND)


class DummyCommand(OneShotCommand):

    def __init__(self):
        super().__init__(DUMMY_COMMAND)
