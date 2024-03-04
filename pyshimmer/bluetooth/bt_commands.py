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
from typing import List, Tuple, Union, Iterable

from pyshimmer.bluetooth.bt_const import *
from pyshimmer.bluetooth.bt_serial import BluetoothSerial

from pyshimmer.dev.base import dr2sr, sr2dr, sec2ticks, ticks2sec
from pyshimmer.dev.channels import ChannelDataType, EChannelType, ESensorGroup, serialize_sensorlist
from pyshimmer.dev.exg import ExGRegister
from pyshimmer.dev.calibration import AllCalibration
from pyshimmer.dev.fw_version import get_firmware_type

from pyshimmer.util import bit_is_set, resp_code_to_bytes, calibrate_u12_adc_value, battery_voltage_to_percent


class DataPacket:
    """Parses data packets received by the Shimmer device

    :arg stream_types: List of tuples that contains each data channel contained in the data packet as well as the
        corresponding data type decoder
    """

    def __init__(self, stream_types: List[Tuple[EChannelType, ChannelDataType]]):
        self._types = stream_types
        self._values = {}

    @property
    def channels(self) -> List[EChannelType]:
        """The data channels present in this data packet

        :return: The channels as list
        """
        return [t for t, _ in self._types]

    @property
    def channel_types(self) -> List[ChannelDataType]:
        """The channel data types that represent the binary data of each channel

        :return: The data types as list
        """
        return [t for _, t in self._types]

    def __getitem__(self, item: EChannelType) -> any:
        """Return the value of a certain data channel

        :param item: The data channel for which to return the data
        :return: The value of the data channel
        """
        return self._values[item]

    def receive(self, ser: BluetoothSerial) -> None:
        """Receive and decode a data packet

        :param ser: The serial device from which to read the data
        """
        ser.read_response(DATA_PACKET)

        for channel_type, channel_dtype in self._types:
            data_bin = ser.read(channel_dtype.size)
            self._values[channel_type] = channel_dtype.decode(data_bin)


class ShimmerCommand(ABC):
    """Abstract base class that represents a command sent to the Shimmer

    """

    @abstractmethod
    def send(self, ser: BluetoothSerial) -> None:
        """Encodes the command and sends it to the Shimmer via the provided serial interface

        :param ser: The serial to use for sending the command
        """
        pass

    def has_response(self) -> bool:
        """Specifies if the command has a response that needs to be read from the return stream

        :return: True if the command has a response, else false
        """
        return False

    def get_response_code(self) -> bytes:
        """The response code of the command

        :return: The response code as a series of bytes, is normally one or two bytes long
        """
        return bytes()

    def receive(self, ser: BluetoothSerial) -> any:
        """Decode the command response from the provided serial interface

        :param ser: The serial from which to decode the response
        :return: The data contained in the response
        """
        return None


class ResponseCommand(ShimmerCommand, ABC):
    """Abstract base class for all commands that feature a command response

    :arg rcode: The response code of the response. Can be a single int for a single-byte response code or
        a tuple of ints or a bytes instance for a multi-byte response code
    """

    def __init__(self, rcode: Union[int, Tuple[int, ...], bytes]):
        self._rcode = resp_code_to_bytes(rcode)

    def has_response(self) -> bool:
        return True

    def get_response_code(self) -> bytes:
        return self._rcode


class OneShotCommand(ShimmerCommand):
    """Class for commands that only send a command code and have no response

    :arg cmd_code: The command code to send
    """

    def __init__(self, cmd_code: int):
        self._code = cmd_code

    def send(self, ser: BluetoothSerial) -> None:
        ser.write_command(self._code)


class GetStringCommand(ResponseCommand):
    """Send a command that features a variable-length string as response

    :arg req_code: The command code of the request
    :arg resp_code: The response code
    :arg encoding: The encoding to use when reading the response string
    """

    def __init__(self, req_code: int, resp_code: Union[int, Tuple[int], bytes], encoding: str = 'utf8'):
        super().__init__(resp_code)
        self._req_code = req_code
        self._encoding = encoding

    def send(self, ser: BluetoothSerial) -> None:
        ser.write_command(self._req_code)

    def receive(self, ser: BluetoothSerial) -> any:
        str_bin = ser.read_response(self._rcode, 'varlen')
        return str_bin.decode(self._encoding)


class SetStringCommand(ShimmerCommand):
    """A command for sending a variable-length string to the device

    :arg req_code: The code of the command request
    :arg str_data: The data to send as part of the request
    :arg encoding: The encoding to use when writing the data to the stream
    """

    def __init__(self, req_code: int, str_data: str, encoding: str = 'utf8'):
        self._req_code = req_code
        self._str_data = str_data
        self._encoding = encoding

    def send(self, ser: BluetoothSerial) -> None:
        str_bin = self._str_data.encode(self._encoding)
        ser.write_command(self._req_code, 'varlen', str_bin)


class GetSamplingRateCommand(ResponseCommand):
    """Retrieve the sampling rate in samples per second

    """

    def __init__(self):
        super().__init__(SAMPLING_RATE_RESPONSE)

    def send(self, ser: BluetoothSerial) -> None:
        ser.write_command(GET_SAMPLING_RATE_COMMAND)

    def receive(self, ser: BluetoothSerial) -> float:
        sr_clock = ser.read_response(SAMPLING_RATE_RESPONSE, arg_format='<H')
        sr = dr2sr(sr_clock)
        return sr


class SetSamplingRateCommand(ShimmerCommand):

    def __init__(self, sr: float):
        self._sr = sr

    def send(self, ser: BluetoothSerial) -> None:
        dr = sr2dr(self._sr)
        ser.write_command(SET_SAMPLING_RATE_COMMAND, "<H", dr)


class GetBatteryCommand(ResponseCommand):
    """Retrieve the battery state

    """

    def __init__(self, in_percent: bool):
        super().__init__(FULL_BATTERY_RESPONSE)
        self._in_percent = in_percent

    def send(self, ser: BluetoothSerial) -> None:
        ser.write_command(GET_BATTERY_COMMAND)

    def receive(self, ser: BluetoothSerial) -> any:
        batt = ser.read_response(self.get_response_code(), arg_format='BBB')
        # Calculation see:
        # http://shimmersensing.com/wp-content/docs/support/documentation/LogAndStream_for_Shimmer3_Firmware_User_Manual_rev0.11a.pdf (Page 17)
        # https://shimmersensing.com/wp-content/docs/support/documentation/Shimmer_User_Manual_rev3p.pdf (Page 53)
        raw_values = batt[1] * 256 + batt[0]
        batt_voltage = calibrate_u12_adc_value(raw_values, 0, 3.0, 1.0) * 1.988
        if self._in_percent:
            return battery_voltage_to_percent(batt_voltage)
        else:
            return batt_voltage


class GetConfigTimeCommand(ResponseCommand):
    """Retrieve the config time that is stored in the Shimmer device configuration file

    """

    def __init__(self):
        super().__init__(CONFIGTIME_RESPONSE)

    def send(self, ser: BluetoothSerial) -> None:
        ser.write_command(GET_CONFIGTIME_COMMAND)

    def receive(self, ser: BluetoothSerial) -> any:
        r = ser.read_response(CONFIGTIME_RESPONSE, arg_format='varlen')
        return int(r)


class SetConfigTimeCommand(ShimmerCommand):
    """Set the config time, which will be stored in the Shimmer device configuration file

    :arg time: The integer value to send
    """

    def __init__(self, time: int):
        self._time = time

    def send(self, ser: BluetoothSerial) -> None:
        time_str = '{:d}'.format(int(self._time))
        time_bin = time_str.encode('ascii')

        ser.write_command(SET_CONFIGTIME_COMMAND, "varlen", time_bin)


class GetRealTimeClockCommand(ResponseCommand):
    """
    Get the real-time clock as UNIX Timestamp in seconds
    """

    def __init__(self):
        super().__init__(RWC_RESPONSE)

    def send(self, ser: BluetoothSerial) -> None:
        ser.write_command(GET_RWC_COMMAND)

    def receive(self, ser: BluetoothSerial) -> float:
        t_ticks = ser.read_response(RWC_RESPONSE, arg_format="<Q")
        return ticks2sec(t_ticks)


class SetRealTimeClockCommand(ShimmerCommand):
    """
    Set the real-time clock as UNIX timestamp in seconds

    :arg ts_sec: The UNIX timestamp in seconds
    """

    def __init__(self, ts_sec: float):
        self._time = int(ts_sec)

    def send(self, ser: BluetoothSerial) -> None:
        t_ticks = sec2ticks(self._time)
        ser.write_command(SET_RWC_COMMAND, '<Q', t_ticks)


class GetStatusCommand(ResponseCommand):
    """Retrieve the current status of the device

    """
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
        super().__init__(FULL_STATUS_RESPONSE)

    def unpack_status_bitfields(self, val: int) -> List[bool]:
        values = [bit_is_set(val, f) for f in self.STATUS_BITFIELDS]
        return values

    def send(self, ser: BluetoothSerial) -> None:
        ser.write_command(GET_STATUS_COMMAND)

    def receive(self, ser: BluetoothSerial) -> any:
        bitfields = ser.read_response(self.get_response_code(), arg_format='B')
        return self.unpack_status_bitfields(bitfields)


class GetFirmwareVersionCommand(ResponseCommand):
    """Retrieve the firmware type and version

    """

    def __init__(self):
        super().__init__(FW_VERSION_RESPONSE)

    def send(self, ser: BluetoothSerial) -> None:
        ser.write_command(GET_FW_VERSION_COMMAND)

    def receive(self, ser: BluetoothSerial) -> any:
        fw_type_bin, major, minor, rel = ser.read_response(
            FW_VERSION_RESPONSE, arg_format='<HHBB')
        fw_type = get_firmware_type(fw_type_bin)
        return fw_type, major, minor, rel


class GetAllCalibrationCommand(ResponseCommand):
    """ Returns all the stored calibration values (84 bytes) in the following order:

            ESensorGroup.ACCEL_LN (21 bytes)
            ESensorGroup.GYRO     (21 bytes)
            ESensorGroup.MAG      (21 bytes)
            ESensorGroup.ACCEL_WR (21 bytes)        

        The breakdown of the kinematic (accel x 2, gyro and mag) calibration values is as follows:
            [bytes  0- 5] offset bias values: 3 (x,y,z) 16-bit signed integers (big endian). 
            [bytes  6-11] sensitivity values: 3 (x,y,z) 16-bit signed integers (big endian). 
            [bytes 12-20] alignment matrix:  9 values    8-bit signed integers.
    """

    def __init__(self):
        super().__init__(ALL_CALIBRATION_RESPONSE)

        self._offset = 0x0
        self._rlen = 0x54  # 84 bytes

    def send(self, ser: BluetoothSerial) -> None:
        ser.write_command(GET_ALL_CALIBRATION_COMMAND)

    def receive(self, ser: BluetoothSerial) -> any:
        ser.read_response(ALL_CALIBRATION_RESPONSE)
        reg_data = ser.read(self._rlen)
        return AllCalibration(reg_data)


class InquiryCommand(ResponseCommand):
    """Perform an inquiry to determine the sample rate, buffer size, and active data channels

    """

    def __init__(self):
        super().__init__(INQUIRY_RESPONSE)

    @staticmethod
    def decode_channel_types(ct_bin: bytes) -> List[EChannelType]:
        ctypes_index = struct.unpack('B' * len(ct_bin), ct_bin)
        ctypes = [BtChannelsByIndex[i] for i in ctypes_index]
        return ctypes

    def send(self, ser: BluetoothSerial) -> None:
        ser.write_command(INQUIRY_COMMAND)

    def receive(self, ser: BluetoothSerial) -> any:
        sr_val, _, n_ch, buf_size = ser.read_response(
            INQUIRY_RESPONSE, arg_format='<HIBB')
        channel_conf = ser.read(n_ch)

        sr = dr2sr(sr_val)
        ctypes = self.decode_channel_types(channel_conf)

        return sr, buf_size, ctypes


class StartStreamingCommand(OneShotCommand):
    """Start streaming data over the Bluetooth channel

    """

    def __init__(self):
        super().__init__(START_STREAMING_COMMAND)


class StopStreamingCommand(OneShotCommand):
    """Stop streaming data over the Bluetooth channel

    """

    def __init__(self):
        super().__init__(STOP_STREAMING_COMMAND)


class GetEXGRegsCommand(ResponseCommand):
    """Retrieve the current state of the ExG chip register

    Queries the values of all registers of the specified chip and returns it as an ExGRegister instance

    :arg chip_id: The chip id, can be one of [0, 1]
    """

    def __init__(self, chip_id: int):
        super().__init__(EXG_REGS_RESPONSE)

        self._chip = chip_id
        self._offset = 0x0
        self._rlen = 0xA

    def send(self, ser: BluetoothSerial) -> None:
        ser.write_command(GET_EXG_REGS_COMMAND, 'BBB',
                          self._chip, self._offset, self._rlen)

    def receive(self, ser: BluetoothSerial) -> any:
        rlen = ser.read_response(EXG_REGS_RESPONSE, arg_format='B')
        if not rlen == self._rlen:
            raise ValueError(
                'Response does not contain required amount of bytes')

        reg_data = ser.read(rlen)
        return ExGRegister(reg_data)


class SetEXGRegsCommand(ShimmerCommand):
    """Set the binary contents of the ExG registers of a chip

    :arg chip_id: The id of the chip, can be one of [0, 1]
    :arg offset: At which offset to write the data
    :arg data: The bytes to write to the registers
    """

    def __init__(self, chip_id: int, offset: int, data: bytes):
        self._chip = chip_id
        self._offset = offset
        self._data = data

    def send(self, ser: BluetoothSerial) -> None:
        dlen = len(self._data)
        ser.write_command(SET_EXG_REGS_COMMAND, 'BBB',
                          self._chip, self._offset, dlen)
        ser.write(self._data)


class GetExperimentIDCommand(GetStringCommand):
    """Retrieve the experiment id

    """

    def __init__(self):
        super().__init__(GET_EXPID_COMMAND, EXPID_RESPONSE)


class SetExperimentIDCommand(SetStringCommand):
    """Set the experiment id

    :arg exp_id: The experiment id as string
    """

    def __init__(self, exp_id: str):
        super().__init__(SET_EXPID_COMMAND, exp_id)


class SetSensorsCommand(ShimmerCommand):

    def __init__(self, sensors: Iterable[ESensorGroup]):
        self._sensors = list(sensors)

    def send(self, ser: BluetoothSerial) -> None:
        bitfield_bin = serialize_sensorlist(self._sensors)
        ser.write_command(SET_SENSORS_COMMAND, "<3s", bitfield_bin)


class GetDeviceNameCommand(GetStringCommand):
    """Get the device name

    """

    def __init__(self):
        super().__init__(GET_SHIMMERNAME_COMMAND, SHIMMERNAME_RESPONSE)


class SetDeviceNameCommand(SetStringCommand):
    """Set the device name

    :arg dev_name: The new device name as string
    """

    def __init__(self, dev_name: str):
        super().__init__(SET_SHIMMERNAME_COMMAND, dev_name)


class SetStatusAckCommand(ShimmerCommand):

    def __init__(self, enabled: bool):
        """Command to enable/disable the ACK byte before status messages

        By default, the Shimmer firmware sends an acknowledgment byte before
        sending unsolicited status messages to the host. This confuses the state
        machine of the Python API but is always expected by the official Shimmer
        software. This command is used by the Python API to automatically disable
        the acknowledgment when connecting to a Shimmer.

        :param enabled: If set to True, the acknowledgment is sent. If set to False,
            the acknowledgment is not sent.
        """
        self._enabled = enabled

    def send(self, ser: BluetoothSerial) -> None:
        ser.write_command(ENABLE_STATUS_ACK_COMMAND, "<B", int(self._enabled))


class StartLoggingCommand(OneShotCommand):
    """Begin logging data to the SD card

    """

    def __init__(self):
        super().__init__(START_LOGGING_COMMAND)


class StopLoggingCommand(OneShotCommand):
    """End logging data to the SD card

    """

    def __init__(self):
        super().__init__(STOP_LOGGING_COMMAND)


class DummyCommand(OneShotCommand):
    """Dummy command that is only acknowledged by the Shimmer but triggers no response

    """

    def __init__(self):
        super().__init__(DUMMY_COMMAND)
