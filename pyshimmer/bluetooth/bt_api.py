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
from queue import Queue, Empty
from threading import Event, Thread
from typing import List, Tuple, Callable

from serial import Serial

from pyshimmer.bluetooth.bt_commands import ShimmerCommand, GetSamplingRateCommand, GetConfigTimeCommand, \
    SetConfigTimeCommand, GetRealTimeClockCommand, SetRealTimeClockCommand, GetStatusCommand, \
    GetFirmwareVersionCommand, InquiryCommand, StartStreamingCommand, StopStreamingCommand, DataPacket, \
    GetEXGRegsCommand, SetEXGRegsCommand, StartLoggingCommand, StopLoggingCommand, GetExperimentIDCommand, \
    SetExperimentIDCommand, GetDeviceNameCommand, SetDeviceNameCommand, DummyCommand
from pyshimmer.bluetooth.bt_const import ACK_COMMAND_PROCESSED, DATA_PACKET
from pyshimmer.bluetooth.bt_serial import BluetoothSerial
from pyshimmer.device import EChannelType, ChDataTypeAssignment, ExGRegister, EFirmwareType, ChannelDataType
from pyshimmer.serial_base import ReadAbort


class RequestCompletion:

    def __init__(self):
        self.__event = Event()

    def set_completed(self) -> None:
        self.__event.set()

    def has_completed(self) -> bool:
        return self.__event.is_set()

    def wait(self) -> None:
        self.__event.wait()


class RequestResponse:

    def __init__(self):
        self.__event = Event()
        self.__r = None

    def has_result(self) -> bool:
        return self.__event.is_set()

    def get_result(self) -> any:
        return self.__r

    def set_result(self, r: any) -> None:
        self.__r = r
        self.__event.set()

    def wait(self) -> any:
        self.__event.wait()
        return self.get_result()


class BluetoothRequestHandler:
    """Base class for the Bluetooth API which handles serial data processing synchronously

    In contrast to the :class:`ShimmerBluetooth` class which uses Threading, this class acts as a base layer that
    operates synchronously and allows for easier testing.

    :arg serial: The serial interface to use
    """

    def __init__(self, serial: BluetoothSerial):
        self._serial = serial

        self._ack_queue = Queue()
        self._resp_queue = Queue()

        self._stream_types = []
        self._stream_cbs = []

    def set_stream_types(self, types: List[Tuple[EChannelType, ChannelDataType]]) -> None:
        """Set the channel types that are streamed as part of the data packets

        :param types: A List of tuples, each containing a channel type and its corresponding data type
        """
        self._stream_types = types

    def add_stream_callback(self, cb: Callable[[DataPacket], None]) -> None:
        """Add a stream callback which is called when a new data packet arrives

        :param cb: a function with a single argument
        """
        self._stream_cbs += [cb]

    def remove_stream_callback(self, cb: Callable[[DataPacket], None]) -> None:
        """Remove the callback from the list of active callbacks

        :param cb: The callback function to remove
        """
        self._stream_cbs.remove(cb)

    def process_single_input_event(self) -> None:
        """Process and read a single input event

        An input event can be a single acknowledgment or a request response. The function does not return anything.
        All data is provided via the completion objects returned when queueing the command.

        """
        peek = self._serial.peek_packed('B')

        if peek == ACK_COMMAND_PROCESSED:
            self._serial.read_ack()

            compl_obj = self._ack_queue.get_nowait()
            compl_obj.set_completed()
        elif peek == DATA_PACKET:
            packet = DataPacket(self._stream_types)
            packet.receive(self._serial)
            [cb(packet) for cb in self._stream_cbs]
        else:
            cmd, return_obj = self._resp_queue.get_nowait()

            resp_code = cmd.get_response_code()
            if peek != resp_code:
                raise ValueError(f'Expecting response code 0x{resp_code:x} but found 0x{peek:x}')

            result = cmd.receive(self._serial)
            return_obj.set_result(result)

    def queue_command(self, cmd: ShimmerCommand) -> Tuple[RequestCompletion, RequestResponse]:
        """Queue a command request for processing

        :param cmd: The command to send to the Shimmer device
        :return: A completion instance and a response instance. The completion instance is always returned and becomes
            true when the command has been processed by the Shimmer. The response object is only returned if the command
            features a response. It holds the response data once the response has been returned by the Shimmer.
        """
        compl_obj = RequestCompletion()
        self._ack_queue.put_nowait(compl_obj)

        if cmd.has_response():
            return_obj = RequestResponse()
            self._resp_queue.put_nowait((cmd, return_obj))
        else:
            return_obj = None

        cmd.send(self._serial)

        return compl_obj, return_obj

    def clear_queues(self) -> None:
        """Clear the internal queues and release any locks held by other threads

        """
        try:
            while True:
                compl: RequestCompletion = self._ack_queue.get_nowait()
                compl.set_completed()
        except Empty:
            pass

        try:
            while True:
                _, resp = self._resp_queue.get_nowait()
                resp.set_result(None)
        except Empty:
            pass


class ShimmerBluetooth:
    """Main API for communicating with the Shimmer via Bluetooth

    :arg serial: The serial interface to use for communication
    """

    def __init__(self, serial: Serial):
        self._serial = BluetoothSerial(serial)
        self._bluetooth = BluetoothRequestHandler(self._serial)

        self._thread = Thread(target=self._run_readloop, daemon=True)

    def __enter__(self):
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.shutdown()

    def initialize(self) -> None:
        """Initialize the reading loop of the API

        Initialize the reading loop by starting a new thread to handle all reads asynchronously
        """
        self._thread.start()

    def shutdown(self) -> None:
        """Shutdown the read loop

        Shutdown the read loop by stopping the read thread
        """
        self._serial.cancel_read()
        self._thread.join()
        self._serial.close()
        self._bluetooth.clear_queues()

    def _run_readloop(self):
        try:
            while True:
                self._bluetooth.process_single_input_event()

        except ReadAbort:
            print('Read loop exciting after cancel request')

    def _process_and_wait(self, cmd):
        compl_obj, return_obj = self._bluetooth.queue_command(cmd)
        compl_obj.wait()

        if return_obj is not None:
            return return_obj.wait()
        return None

    def add_stream_callback(self, cb: Callable[[DataPacket], None]) -> None:
        """Add a stream callback which is called when a new data packet arrives

        :param cb: a function with a single argument
        """
        self._bluetooth.add_stream_callback(cb)

    def remove_stream_callback(self, cb: Callable[[DataPacket], None]) -> None:
        """Remove the callback from the list of active callbacks

        :param cb: The callback function to remove
        """
        self._bluetooth.remove_stream_callback(cb)

    def get_sampling_rate(self) -> float:
        """Retrieve the sampling rate of the device

        :return: The sampling rate as floating point value in samples per second
        """
        return self._process_and_wait(GetSamplingRateCommand())

    def get_config_time(self) -> int:
        """Get the config time from the device as configured in the configuration file

        :return: The config time as integer
        """
        return self._process_and_wait(GetConfigTimeCommand())

    def set_config_time(self, time: int) -> None:
        """Set the config time of the device

        :arg time: The configuration time that will be set in the configuration of the Shimmer
        """
        self._process_and_wait(SetConfigTimeCommand(time))

    def get_rtc(self) -> float:
        """Retrieve the current value of the onboard real-time clock

        :return: The current time of the device in seconds as UNIX timestamp
        """
        return self._process_and_wait(GetRealTimeClockCommand())

    def set_rtc(self, time_sec: float) -> None:
        """Set the value of the onboard real-time clock

        Should be set as a UTC UNIX timestamp such that the resulting recordings have universal timestamps

        :param time_sec: The UNIX timestamp in seconds
        """
        self._process_and_wait(SetRealTimeClockCommand(time_sec))

    def get_status(self) -> List[bool]:
        """Get the status of the device

        :return: A list of 8 bools which signal:
            dev_docked, dev_sensing, rtc_set, dev_logging, dev_streaming, sd_card_present, sd_error, status_red_led
        """
        return self._process_and_wait(GetStatusCommand())

    def get_firmware_version(self) -> Tuple[EFirmwareType, int, int, int]:
        """Get the version of the running firmware

        :return: A tuple of four values:
            - The firmware type as enum, i.e. SDLog, LogAndStream, ...
            - the major version as int
            - the minor version as int
            - the patch level as int
        """
        return self._process_and_wait(GetFirmwareVersionCommand())

    def get_exg_register(self, chip_id: int) -> ExGRegister:
        """Get the current configuration of one of the two ExG registers of the device

        Note that this command only returns meaningful results if the device features ECG chips

        :param chip_id: The ID of the chip, one of [0, 1]
        :return: An ExGRegister object that presents the register contents in an easily processable manner
        """
        return self._process_and_wait(GetEXGRegsCommand(chip_id))

    def set_exg_register(self, chip_id: int, offset: int, data: bytes) -> None:
        """Configure part of the memory of the ExG registers

        :param chip_id: The ID of the chip, one of [0, 1]
        :param offset: The offset at which to write the data bytes
        :param data: The data bytes to write
        """
        self._process_and_wait(SetEXGRegsCommand(chip_id, offset, data))

    def get_device_name(self) -> str:
        """Retrieve the device name

        :return: The device name as string
        """
        return self._process_and_wait(GetDeviceNameCommand())

    def set_device_name(self, dev_name: str) -> None:
        """Set the device name

        :param dev_name: The device name to set
        """
        self._process_and_wait(SetDeviceNameCommand(dev_name))

    def get_experiment_id(self) -> str:
        """Retrieve the experiment id as string

        :return: The experiment ID as string
        """
        return self._process_and_wait(GetExperimentIDCommand())

    def set_experiment_id(self, exp_id: str) -> None:
        """Set the experiment ID for the device

        :param exp_id: The id to set for the device
        """
        self._process_and_wait(SetExperimentIDCommand(exp_id))

    def get_inquiry(self) -> Tuple[float, int, List[EChannelType]]:
        """Perform inquiry command

        :return: A tuple of 3 values:
            - The sampling rate as float
            - The buf size of the device
            - The active data channels of the device as list, does not include the TIMESTAMP channel
        """
        return self._process_and_wait(InquiryCommand())

    def get_data_types(self):
        """Get the active data channels of the device

        These data channels will be contained in a DataPacket when streaming

        :return: A list of data channels, always containing the TIMESTAMP channel
        """
        _, _, ctypes = self.get_inquiry()
        # The Timestamp is always present in data packets
        ctypes = [EChannelType.TIMESTAMP] + ctypes

        return ctypes

    def start_streaming(self) -> None:
        """Start streaming data

        """
        ctypes = self.get_data_types()

        stream_types = [(t, ChDataTypeAssignment[t]) for t in ctypes]
        self._bluetooth.set_stream_types(stream_types)

        self._process_and_wait(StartStreamingCommand())

    def stop_streaming(self) -> None:
        """Stop streaming data

        Note that the interface will possibly return more data packets that have already been received and are in the
        input buffer.

        """
        self._process_and_wait(StopStreamingCommand())

    def start_logging(self) -> None:
        """Start logging data to the SD card of the device

        """
        self._process_and_wait(StartLoggingCommand())

    def stop_logging(self) -> None:
        """Stop logging data to the SD card of the device

        """
        self._process_and_wait(StopLoggingCommand())

    def send_ping(self) -> None:
        """Send a ping command to the device

        The command can be used to test the connection. It does not return anything.
        """
        self._process_and_wait(DummyCommand())
