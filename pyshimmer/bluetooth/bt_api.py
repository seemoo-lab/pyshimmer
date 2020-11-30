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
from queue import Queue
from threading import Event, Thread
from typing import List, Tuple

from serial import Serial

from pyshimmer.bluetooth.bt_commands import ShimmerCommand, GetSamplingRateCommand, GetConfigTimeCommand, \
    SetConfigTimeCommand, GetRealTimeClockCommand, SetRealTimeClockCommand, GetStatusCommand, \
    GetFirmwareVersionCommand, InquiryCommand, StartStreamingCommand, StopStreamingCommand, DataPacket, \
    GetEXGRegsCommand, SetEXGRegsCommand, StartLoggingCommand, StopLoggingCommand, GetExperimentIDCommand, \
    SetExperimentIDCommand, GetDeviceNameCommand, SetDeviceNameCommand, DummyCommand
from pyshimmer.bluetooth.bt_const import ACK_COMMAND_PROCESSED, DATA_PACKET
from pyshimmer.bluetooth.bt_serial import BluetoothSerial
from pyshimmer.device import EChannelType, ChDataTypeAssignment, ExGRegister, EFirmwareType
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


class ShimmerBluetooth:

    def __init__(self, serial: Serial):
        self._serial = BluetoothSerial(serial)
        self._thread = Thread(target=self._run_readloop, daemon=True)
        self._stop = False

        self._ack_queue = Queue()
        self._resp_queue = Queue()

        self._stream_types = []
        self._stream_cbs = []

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

    def _run_readloop(self):
        try:
            self._readloop()
        except ReadAbort:
            print('Read loop exciting after cancel request')

    def _readloop(self):
        while True:
            peek = self._serial.peek()

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

    def _process_command(self, cmd: ShimmerCommand):
        compl_obj = RequestCompletion()
        self._ack_queue.put_nowait(compl_obj)

        if cmd.has_response():
            return_obj = RequestResponse()
            self._resp_queue.put_nowait((cmd, return_obj))
        else:
            return_obj = None

        cmd.send(self._serial)

        return compl_obj, return_obj

    def _process_and_wait(self, cmd):
        compl_obj, return_obj = self._process_command(cmd)
        compl_obj.wait()

        if return_obj is not None:
            return return_obj.wait()
        return None

    def add_stream_callback(self, cb):
        self._stream_cbs += [cb]

    def remove_stream_callback(self, cb):
        self._stream_cbs.remove(cb)

    def get_sampling_rate(self) -> float:
        return self._process_and_wait(GetSamplingRateCommand())

    def get_config_time(self) -> int:
        return self._process_and_wait(GetConfigTimeCommand())

    def set_config_time(self, ut_ms: int) -> None:
        """Set the config time of the device as unix timestamp in milliseconds

        Set the time of the device to the supplied Unix millisecond timestamp (since Jan 1st, 1970). See Python
        time.time() for more information.

        Args:
            ut_ms: An integer that represents the elapsed milliseconds since Jan 1st, 1970.
        """
        self._process_and_wait(SetConfigTimeCommand(ut_ms))

    def get_rtc(self) -> int:
        return self._process_and_wait(GetRealTimeClockCommand())

    def set_rtc(self, ut_ms: int) -> None:
        self._process_and_wait(SetRealTimeClockCommand(ut_ms))

    def get_status(self) -> List[bool]:
        return self._process_and_wait(GetStatusCommand())

    def get_firmware_version(self) -> Tuple[EFirmwareType, int, int, int]:
        return self._process_and_wait(GetFirmwareVersionCommand())

    def get_exg_register(self, chip_id) -> ExGRegister:
        return self._process_and_wait(GetEXGRegsCommand(chip_id))

    def set_exg_register(self, chip_id, offset, data) -> None:
        self._process_and_wait(SetEXGRegsCommand(chip_id, offset, data))

    def get_device_name(self) -> str:
        return self._process_and_wait(GetDeviceNameCommand())

    def set_device_name(self, dev_name: str) -> None:
        self._process_and_wait(SetDeviceNameCommand(dev_name))

    def get_experiment_id(self) -> str:
        return self._process_and_wait(GetExperimentIDCommand())

    def set_experiment_id(self, exp_id: str) -> None:
        self._process_and_wait(SetExperimentIDCommand(exp_id))

    def get_inquiry(self) -> Tuple[float, int, List[EChannelType]]:
        return self._process_and_wait(InquiryCommand())

    def get_data_types(self):
        _, _, ctypes = self.get_inquiry()
        # The Timestamp is always present in data packets
        ctypes = [EChannelType.TIMESTAMP] + ctypes

        return ctypes

    def start_streaming(self) -> None:
        ctypes = self.get_data_types()

        self._stream_types = [(t, ChDataTypeAssignment[t]) for t in ctypes]
        self._process_and_wait(StartStreamingCommand())

    def stop_streaming(self) -> None:
        self._process_and_wait(StopStreamingCommand())

    def start_logging(self) -> None:
        self._process_and_wait(StartLoggingCommand())

    def stop_logging(self) -> None:
        self._process_and_wait(StopLoggingCommand())

    def send_ping(self) -> None:
        self._process_and_wait(DummyCommand())
