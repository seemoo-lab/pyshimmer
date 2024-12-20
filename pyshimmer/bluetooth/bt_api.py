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
from typing import List, Tuple, Callable, Iterable, Optional

from serial import Serial

from pyshimmer.bluetooth.bt_commands import ShimmerCommand, GetSamplingRateCommand, GetConfigTimeCommand, \
    SetConfigTimeCommand, GetRealTimeClockCommand, SetRealTimeClockCommand, GetStatusCommand, \
    GetFirmwareVersionCommand, InquiryCommand, StartStreamingCommand, StopStreamingCommand, DataPacket, \
    GetEXGRegsCommand, SetEXGRegsCommand, StartLoggingCommand, StopLoggingCommand, GetExperimentIDCommand, \
    SetExperimentIDCommand, GetDeviceNameCommand, SetDeviceNameCommand, DummyCommand, GetBatteryCommand, \
    SetSamplingRateCommand, SetSensorsCommand, SetStatusAckCommand, AllCalibration, GetAllCalibrationCommand
from pyshimmer.bluetooth.bt_const import ACK_COMMAND_PROCESSED, DATA_PACKET, FULL_STATUS_RESPONSE, INSTREAM_CMD_RESPONSE
from pyshimmer.bluetooth.bt_serial import BluetoothSerial
from pyshimmer.dev.channels import ChDataTypeAssignment, ChannelDataType, EChannelType, ESensorGroup
from pyshimmer.dev.exg import ExGRegister
from pyshimmer.dev.fw_version import EFirmwareType, FirmwareVersion, FirmwareCapabilities
from pyshimmer.serial_base import ReadAbort
from pyshimmer.util import fmt_hex, PeekQueue


class RequestCompletion:
    """
    Returned by the Bluetooth API upon sending a request. Signals the completion of a request when the API receives
    the corresponding acknowledgment.
    """

    def __init__(self):
        self.__event = Event()

    def set_completed(self) -> None:
        self.__event.set()

    def has_completed(self) -> bool:
        return self.__event.is_set()

    def wait(self) -> None:
        self.__event.wait()


class RequestResponse:
    """
    Returned by the Bluetooth API upon sending a request that features a response. Returns the request response data
    upon completion.
    """

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
        self._resp_queue = PeekQueue()

        self._stream_types = []
        self._stream_cbs = []
        self._status_cbs = []

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

    def add_status_callback(self, cb: Callable[[List[bool]], None]) -> None:
        """Add a status callback which is called when a new status update from the Shimmer arrives

        :param cb: a function with a single argument. The argument is the same value is the return value of the
            :meth:`pyshimmer.bluetooth.bt_api.ShimmerBluetooth.get_status` method.
        """
        self._status_cbs += [cb]

    def remove_status_callback(self, cb: Callable[[List[bool]], None]) -> None:
        """Remove the callback from the list of active callbacks

        :param cb: The callback function to remove
        """
        self._status_cbs.remove(cb)

    def _process_ack(self):
        self._serial.read_ack()
        compl_obj, cmd_resp_pair = self._ack_queue.get_nowait()

        if None not in cmd_resp_pair:
            # We are expecting a response
            self._resp_queue.put_nowait(cmd_resp_pair)

        compl_obj.set_completed()

    def _process_data_packet(self):
        packet = DataPacket(self._stream_types)
        packet.receive(self._serial)

        for cb in self._stream_cbs:
            cb(packet)

    def _process_in_stream_resp(self):
        peek = self._serial.peek(len(FULL_STATUS_RESPONSE))

        if peek == FULL_STATUS_RESPONSE:
            # The packet is a status response, which we need to handle separately
            self._process_status_response()
        else:
            # We don't know exactly what it is, but it must have been triggered by a command, so we simply
            # process it as part of the reqular queue handling
            self._process_resp_from_queue()

    def _process_status_response(self):
        cmd_resp_pair = self._resp_queue.peek()

        if cmd_resp_pair is not None and isinstance(cmd_resp_pair[0], GetStatusCommand):
            # We have received a Status Response and have are expecting a response from a command
            # ---> Handle it like a regular command
            self._process_resp_from_queue()
        else:
            # We have received a Status Response but are not expecting one
            # ---> Handle it as a pushed Status Update
            self._process_status_update()

    def _process_status_update(self):
        # Called if the status response was not triggered by a command but sent by the Shimmer as the result of
        # an event
        status_cmd = GetStatusCommand()
        r = status_cmd.receive(self._serial)

        for cb in self._status_cbs:
            cb(r)

    def _process_resp_from_queue(self):
        cmd, return_obj = self._resp_queue.get_nowait()

        resp_code = cmd.get_response_code()
        peek = self._serial.peek(len(resp_code))

        if peek != resp_code:
            raise ValueError(f'Expecting response code {fmt_hex(resp_code)} but found {fmt_hex(peek)}')

        result = cmd.receive(self._serial)
        return_obj.set_result(result)

    def process_single_input_event(self) -> None:
        """Process and read a single input event

        An input event can be a single acknowledgment or a request response. The function does not return anything.
        All data is provided via the completion objects returned when queueing the command.

        """
        peek = self._serial.peek_packed('B')

        if peek == ACK_COMMAND_PROCESSED:
            self._process_ack()
        elif peek == DATA_PACKET:
            self._process_data_packet()
        elif peek == INSTREAM_CMD_RESPONSE:
            self._process_in_stream_resp()
        else:
            self._process_resp_from_queue()

    def queue_command(self, cmd: ShimmerCommand) -> Tuple[RequestCompletion, RequestResponse]:
        """Queue a command request for processing

        :param cmd: The command to send to the Shimmer device
        :return: A completion instance and a response instance. The completion instance is always returned and becomes
            true when the command has been processed by the Shimmer. The response object is only returned if the command
            features a response. It holds the response data once the response has been returned by the Shimmer.
        """
        resp_obj = None
        cmd_resp_pair = (None, None)
        compl_obj = RequestCompletion()

        if cmd.has_response():
            resp_obj = RequestResponse()
            cmd_resp_pair = (cmd, resp_obj)

        self._ack_queue.put_nowait((compl_obj, cmd_resp_pair))
        cmd.send(self._serial)

        return compl_obj, resp_obj

    def clear_queues(self) -> None:
        """Clear the internal queues and release any locks held by other threads

        """
        try:
            while True:
                compl, (cmd, resp) = self._ack_queue.get_nowait()
                compl.set_completed()

                if resp is not None:
                    resp.set_result(None)
        except Empty:
            pass

        try:
            while True:
                _, resp = self._resp_queue.get_nowait()
                resp.set_result(None)
        except Empty:
            pass


class ShimmerBluetooth:

    def __init__(self, serial: Serial, disable_status_ack: bool = True):
        """API for communicating with the Shimmer via Bluetooth

        This class implements support for talking to the Shimmer LogAndStream firmware via Bluetooth.
        Each command is encapsulated as a method that can be called to invoke the corresponding command.
        All commands are executed synchronously. This means that the method call will block until the
        Shimmer has processed the request and responded.

        :param serial: The serial channel that encapsulates the rfcomm Bluetooth connection to the Shimmer
        :param disable_status_ack: Starting with LogAndStream firmware version 0.15.4, the vanilla firmware
            supports disabling the acknowledgment byte before status messages. This removes the need for
            running a custom firmware version on the Shimmer. If this flag is set to True, the API will
            query the firmware version of the Shimmer and automatically send a command to disable the status
            acknowledgment byte at startup. You can set it to True if you don't want this or if it causes
            trouble with your firmware version.
        """
        self._serial = BluetoothSerial(serial)
        self._bluetooth = BluetoothRequestHandler(self._serial)

        self._thread = Thread(target=self._run_readloop, daemon=True)

        self._initialized = False
        self._disable_ack = disable_status_ack

        self._fw_version: Optional[FirmwareVersion] = None
        self._fw_caps: Optional[FirmwareCapabilities] = None

    @property
    def initialized(self) -> bool:
        """Specifies if the connection was initialized

        This property helps to determine if the capabilities property will return a valid value.

        :return: True if initialize() was called, otherwise False
        """
        return self._initialized

    @property
    def capabilities(self) -> FirmwareCapabilities:
        """Return the capabilities of the device firmware

        This property shall only be accessed after invoking initialize().

        :return: A FirmwareCapabilities instance representing the version and capabilities of the firmware
        """
        return self._fw_caps

    def __enter__(self):
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.shutdown()

    def _set_fw_capabilities(self) -> None:
        fw_type, fw_ver = self.get_firmware_version()
        self._fw_caps = FirmwareCapabilities(fw_type, fw_ver)

    def initialize(self) -> None:
        """Initialize the Bluetooth connection

        This method must be invoked before sending commands to the Shimmer. It queries the Shimmer version,
        optionally disables the status acknowledgment and starts the read loop.
        """
        self._thread.start()

        self._set_fw_capabilities()

        if self.capabilities.supports_ack_disable and self._disable_ack:
            self.set_status_ack(enabled=False)

        self._initialized = True

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

    def add_status_callback(self, cb: Callable[[List[bool]], None]) -> None:
        """Add a status callback which is called when a new status update from the Shimmer arrives

        :param cb: a function with a single argument. The argument is the same value is the return value of the
            :meth:`pyshimmer.bluetooth.bt_api.ShimmerBluetooth.get_status` method.
        """
        self._bluetooth.add_status_callback(cb)

    def remove_status_callback(self, cb: Callable[[List[bool]], None]) -> None:
        """Remove the callback from the list of active callbacks

        :param cb: The callback function to remove
        """
        self._bluetooth.remove_status_callback(cb)

    def get_sampling_rate(self) -> float:
        """Retrieve the sampling rate of the device

        :return: The sampling rate as floating point value in samples per second
        """
        return self._process_and_wait(GetSamplingRateCommand())

    def set_sampling_rate(self, sr: float) -> None:
        """Set the active sampling rate for the device

        :param sr: The sampling rate in Hertz
        """
        self._process_and_wait(SetSamplingRateCommand(sr))

    def get_battery_state(self, in_percent: bool) -> float:
        """Retrieve the battery state of the device

        :param in_percent: True: calculate battery state in percent; False: calculate battery state in Volt
        :return: The battery state in percent / Volt
        """
        return self._process_and_wait(GetBatteryCommand(in_percent))

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

    def set_sensors(self, sensors: Iterable[ESensorGroup]) -> None:
        """Set the active sensors for sampling

        This command will activate the specified list of sensors and deactivate all other sensors.

        :param sensors: A list of sensors to activate
        """
        self._process_and_wait(SetSensorsCommand(sensors))

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

    def get_firmware_version(self) -> Tuple[EFirmwareType, FirmwareVersion]:
        """Get the version of the running firmware

        :return: The firmware type as enum, i.e. SDLog or LogAndStream
            and the numeric firmware version
        """
        fw_type, major, minor, rel = self._process_and_wait(GetFirmwareVersionCommand())
        fw_version = FirmwareVersion(major, minor, rel)

        return fw_type, fw_version

    def get_exg_register(self, chip_id: int) -> ExGRegister:
        """Get the current configuration of one of the two ExG registers of the device

        Note that this command only returns meaningful results if the device features ECG chips

        :param chip_id: The ID of the chip, one of [0, 1]
        :return: An ExGRegister object that presents the register contents in an easily processable manner
        """
        return self._process_and_wait(GetEXGRegsCommand(chip_id))

    def get_all_calibration(self) -> AllCalibration:
        """Gets all calibration data from sensor
        :return: An AllCalibration object that presents the calibration contents in an easily processable manner
        """
        return self._process_and_wait(GetAllCalibrationCommand())

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

    def set_status_ack(self, enabled: bool) -> None:
        """Send a command to enable or disable the status acknowledgment

        This command should normally not be called directly. If enabled in the constructor, the command
        will automatically be sent to the Shimmer if the firmware supports it. It can be used to make
        vanilla firmware versions compatible with the state machine of the Python API.

        :param enabled: If set to True, enable status acknowledgment byte. This will make the
            firmware incompatible to the Python API. If set to False, disable sending the status ack.
            In this state, the firmware is compatible to the Python API.
        """
        self._process_and_wait(SetStatusAckCommand(enabled))
