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
from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, Future
from typing import BinaryIO
from unittest import TestCase

import pytest

from pyshimmer.bluetooth.bt_api import BluetoothRequestHandler, ShimmerBluetooth
from pyshimmer.bluetooth.bt_commands import (
    GetDeviceNameCommand,
    SetDeviceNameCommand,
    DataPacket,
    GetStatusCommand,
    GetStringCommand,
    ResponseCommand,
)
from pyshimmer.bluetooth.bt_serial import BluetoothSerial
from pyshimmer.dev.channels import ChDataTypeAssignment, EChannelType
from pyshimmer.dev.fw_version import FirmwareVersion, EFirmwareType
from pyshimmer.dev.revisions import (
    HardwareVersion,
    HardwareRevision,
    HW_REVISIONS,
)
from pyshimmer.test_util import PTYSerialMockCreator


class TestBluetoothRequestHandler:

    @pytest.fixture
    def mock_creator(self) -> PTYSerialMockCreator:
        mock_creator = PTYSerialMockCreator()
        mock_creator.create_mock()

        yield mock_creator

        mock_creator.close()

    @pytest.fixture(params=HW_REVISIONS)
    def revision(self, request) -> HardwareRevision:
        return request.param

    @pytest.fixture
    def mock_serial(self, mock_creator: PTYSerialMockCreator) -> BluetoothSerial:
        bt_serial = BluetoothSerial(mock_creator.slave_serial)
        return bt_serial

    @pytest.fixture
    def sot(
        self, mock_serial: BluetoothSerial, revision: HardwareRevision
    ) -> BluetoothRequestHandler:
        handler = BluetoothRequestHandler(mock_serial, revision)
        return handler

    def test_add_remove_stream_cb(self, sot: BluetoothRequestHandler):
        def cb(_):
            pass

        sot.add_stream_callback(cb)
        sot.remove_stream_callback(cb)

    def test_add_remove_status_cb(self, sot: BluetoothRequestHandler):
        def cb(_):
            pass

        sot.add_status_callback(cb)
        sot.remove_status_callback(cb)

    def test_enque_command(
        self,
        mock_creator: PTYSerialMockCreator,
        sot: BluetoothRequestHandler,
        revision: HardwareRevision,
    ):
        cmd = GetDeviceNameCommand(revision)
        compl, resp = sot.queue_command(cmd)

        assert compl.has_completed() is False
        assert resp.has_result() is False

        r = mock_creator.read_from_master(1)
        assert r == b"\x7b"

        mock_creator.write_to_master(b"\xff")
        sot.process_single_input_event()

        assert compl.has_completed() is True
        assert resp.has_result() is False

        mock_creator.write_to_master(b"\x7a\x05\x53\x5f\x50\x50\x47")
        sot.process_single_input_event()

        assert resp.has_result() is True
        assert resp.get_result() == "S_PPG"

    def test_enqueue_multibyte(
        self,
        mock_creator: PTYSerialMockCreator,
        revision: HardwareRevision,
        sot: BluetoothRequestHandler,
    ):
        cmd = GetStringCommand(revision, 0x10, b"\x0a\x0b")
        compl, resp = sot.queue_command(cmd)

        r = mock_creator.read_from_master(1)
        assert r == b"\x10"

        mock_creator.write_to_master(b"\xff")
        sot.process_single_input_event()

        mock_creator.write_to_master(b"\x0a\x0b\x02ab")
        sot.process_single_input_event()

        assert compl.has_completed() is True
        assert resp.has_result() is True
        assert resp.get_result() == "ab"

    def test_enqueue_multiple_commands(
        self,
        mock_creator: PTYSerialMockCreator,
        revision: HardwareRevision,
        sot: BluetoothRequestHandler,
    ):
        cmd1 = GetDeviceNameCommand(revision)
        cmd2 = GetStatusCommand(revision)

        compl1, resp1 = sot.queue_command(cmd1)
        compl2, resp2 = sot.queue_command(cmd2)

        r = mock_creator.read_from_master(2)
        assert r == b"\x7b\x72"

        mock_creator.write_to_master(b"\xff\x7a\x05\x53\x5f\x50\x50\x47")
        mock_creator.write_to_master(b"\xff\x8a\x71\x21")

        sot.process_single_input_event()
        assert compl1.has_completed() is True

        sot.process_single_input_event()
        assert resp1.has_result() is True
        assert resp1.get_result() == "S_PPG"

        sot.process_single_input_event()
        assert compl2.has_completed() is True

        sot.process_single_input_event()
        assert resp2.has_result() is True
        assert resp2.get_result() == [
            True,
            False,
            False,
            False,
            False,
            True,
            False,
            False,
        ]

    def test_queue_command_no_resp(
        self,
        mock_creator: PTYSerialMockCreator,
        revision: HardwareRevision,
        sot: BluetoothRequestHandler,
    ):
        cmd = SetDeviceNameCommand(revision, "S_PPG")
        compl, resp = sot.queue_command(cmd)

        assert compl.has_completed() is False
        assert resp is None

        r = mock_creator.read_from_master(7)
        assert r == b"\x79\x05S_PPG"

        mock_creator.write_to_master(b"\xff")
        sot.process_single_input_event()
        assert compl.has_completed() is True

    def test_queue_unknown_instream(
        self,
        mock_creator: PTYSerialMockCreator,
        revision: HardwareRevision,
        sot: BluetoothRequestHandler,
    ):
        class InStreamCommand(ResponseCommand):

            def __init__(self):
                super().__init__(revision, b"\x8a\x42")

            def send(self, ser: BluetoothSerial) -> None:
                ser.write(b"\x42")

            def receive(self, ser: BluetoothSerial) -> any:
                return ser.read_response(b"\x8a\x42")

        compl, resp = sot.queue_command(InStreamCommand())

        r = mock_creator.read_from_master(1)
        assert r == b"\x42"

        mock_creator.write_to_master(b"\xff\x8a\x42")
        sot.process_single_input_event()
        assert compl.has_completed() is True

        sot.process_single_input_event()
        assert resp.has_result() is True

    def test_get_status_command(
        self,
        mock_creator: PTYSerialMockCreator,
        revision: HardwareRevision,
        sot: BluetoothRequestHandler,
    ):

        cmd = GetStatusCommand(revision)
        compl, resp = sot.queue_command(cmd)

        assert compl.has_completed() is False
        assert resp.has_result() is False

        r = mock_creator.read_from_master(1)
        assert r == b"\x72"

        mock_creator.write_to_master(b"\xff\x8a\x71\x21")
        sot.process_single_input_event()
        assert compl.has_completed() is True
        assert resp.has_result() is False

        sot.process_single_input_event()
        assert resp.has_result() is True
        assert resp.get_result() == [
            True,
            False,
            False,
            False,
            False,
            True,
            False,
            False,
        ]

    def test_incorrect_resp_code_fail(
        self,
        mock_creator: PTYSerialMockCreator,
        revision: HardwareRevision,
        sot: BluetoothRequestHandler,
    ):

        cmd = GetDeviceNameCommand(revision)
        _ = sot.queue_command(cmd)

        mock_creator.write_to_master(b"\xff\xfe")
        sot.process_single_input_event()

        with pytest.raises(ValueError):
            sot.process_single_input_event()

    def test_data_packet(
        self,
        mock_creator: PTYSerialMockCreator,
        sot: BluetoothRequestHandler,
    ):
        results: list[DataPacket] = []

        data_pkt_1 = b"\x00\xde\xd0\xb2\x26\x07"
        data_pkt_2 = b"\x00\x1e\xd1\xb2\xfc\x06"

        ch_types = [EChannelType.TIMESTAMP, EChannelType.INTERNAL_ADC_A1]
        sot.stream_types = [(c, ChDataTypeAssignment[c]) for c in ch_types]
        sot.add_stream_callback(results.append)

        mock_creator.write_to_master(data_pkt_1)
        mock_creator.write_to_master(data_pkt_2)

        sot.process_single_input_event()
        assert len(results) == 1
        pkt = results[0]

        assert pkt.channels == ch_types
        assert pkt[EChannelType.TIMESTAMP] == 0xB2D0DE
        assert pkt[EChannelType.INTERNAL_ADC_A1] == 0x0726

        sot.process_single_input_event()
        assert len(results) == 2
        pkt = results[1]

        assert pkt.channels == ch_types
        assert pkt[EChannelType.TIMESTAMP] == 0xB2D11E
        assert pkt[EChannelType.INTERNAL_ADC_A1] == 0x06FC

    def test_get_status_response(
        self, mock_creator: PTYSerialMockCreator, sot: BluetoothRequestHandler
    ):
        status_resp: list[list[bool]] = []

        stat_pkt_1 = b"\x8a\x71\x20"
        stat_pkt_2 = b"\x8a\x71\x21"
        sot.add_status_callback(status_resp.append)

        mock_creator.write_to_master(stat_pkt_1)
        mock_creator.write_to_master(stat_pkt_2)

        sot.process_single_input_event()
        assert len(status_resp) == 1
        assert status_resp[0] == [False, False, False, False, False, True, False, False]

        sot.process_single_input_event()
        assert len(status_resp) == 2
        assert status_resp[1] == [True, False, False, False, False, True, False, False]

    def test_get_status_response_update_mixed(
        self,
        mock_creator: PTYSerialMockCreator,
        revision: HardwareRevision,
        sot: BluetoothRequestHandler,
    ):
        stat_pkt_1 = b"\x8a\x71\x20"
        stat_pkt_2 = b"\x8a\x71\x21"

        status_resp: list[list[bool]] = []
        sot.add_status_callback(status_resp.append)

        compl, resp = sot.queue_command(GetStatusCommand(revision))
        r = mock_creator.read_from_master(1)
        assert r == b"\x72"

        mock_creator.write_to_master(b"\xff" + stat_pkt_1)
        mock_creator.write_to_master(stat_pkt_2)

        sot.process_single_input_event()
        assert compl.has_completed() is True

        sot.process_single_input_event()
        assert resp.has_result() is True
        assert resp.get_result() == [
            False,
            False,
            False,
            False,
            False,
            True,
            False,
            False,
        ]

        sot.process_single_input_event()
        assert len(status_resp) == 1
        assert status_resp[0] == [True, False, False, False, False, True, False, False]

    def test_clear_queues(
        self,
        mock_creator: PTYSerialMockCreator,
        revision: HardwareRevision,
        sot: BluetoothRequestHandler,
    ):
        compl1, resp1 = sot.queue_command(GetDeviceNameCommand(revision))
        compl2, resp2 = sot.queue_command(GetDeviceNameCommand(revision))

        assert compl1.has_completed() is False
        assert resp1.has_result() is False

        # Ensure that the first command has been passed into the response queue
        mock_creator.write_to_master(b"\xff")
        sot.process_single_input_event()

        assert compl1.has_completed() is True
        assert resp1.has_result() is False

        assert compl2.has_completed() is False
        assert resp2.has_result() is False

        sot.clear_queues()

        assert compl1.has_completed() is True
        assert resp1.has_result() is True
        assert resp1.get_result() is None

        assert compl2.has_completed() is True
        assert resp2.has_result() is True
        assert resp2.get_result() is None


class ShimmerBluetoothIntegrationTest(TestCase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._executor = ThreadPoolExecutor(max_workers=1)

        self._mock_creator: PTYSerialMockCreator | None = None
        self._sot: ShimmerBluetooth | None = None

        self._master: BinaryIO | None = None

    def _submit_handler_fn(
        self, fn: Callable[[BinaryIO, ShimmerBluetooth], any]
    ) -> Future:
        return self._executor.submit(fn, self._master, self._sot)

    def _submit_req_resp_handler(self, req_len: int, resp: bytes) -> Future:
        def master_fn(master: BinaryIO, _) -> bytes:
            req = bytes()
            while len(req) < req_len:
                req += master.read(req_len - len(req))

            master.write(resp)
            return req

        return self._submit_handler_fn(master_fn)

    def do_setup(self, initialize: bool = True, **kwargs) -> None:
        self._mock_creator = PTYSerialMockCreator()
        serial, self._master = self._mock_creator.create_mock()

        self._sot = ShimmerBluetooth(serial, **kwargs)

        if initialize:
            # The Bluetooth API automatically requests the firmware version upon
            # initialization. We must prepare a proper response beforehand.
            req_future_fw = self._submit_req_resp_handler(
                req_len=1, resp=b"\xff\x2f\x03\x00\x00\x00\x0b\x00"
            )
            req_future_hw = self._submit_req_resp_handler(
                req_len=1, resp=b"\xff\x25\x03"
            )
            self._sot.initialize()

            # Check that it properly asked for the firmware version
            result = req_future_fw.result()
            assert result == b"\x2e"
            result = req_future_hw.result()
            assert result == b"\x3f"

    def tearDown(self) -> None:
        self._sot.shutdown()
        self._mock_creator.close()

    def test_context_manager(self):
        self.do_setup(initialize=False)

        # The Bluetooth API automatically requests the firmware version upon
        # initialization. We must prepare a proper response beforehand.
        req_future_fw = self._submit_req_resp_handler(
            req_len=1, resp=b"\xff\x2f\x03\x00\x00\x00\x0b\x00"
        )
        req_future_hw = self._submit_req_resp_handler(req_len=1, resp=b"\xff\x25\x03")
        with self._sot:
            # We check that the API properly asked for the firmware version
            req_data_fw = req_future_fw.result()
            self.assertEqual(req_data_fw, b"\x2e")
            req_data_hw = req_future_hw.result()
            self.assertEqual(req_data_hw, b"\x3f")

            # It should now be in an initialized state
            self.assertTrue(self._sot.initialized)

    def test_version_and_capabilities(self):
        self.do_setup(initialize=True)

        self.assertTrue(self._sot.initialized)
        self.assertIsNotNone(self._sot.capabilities)
        self.assertEqual(self._sot.capabilities.fw_type, EFirmwareType.LogAndStream)
        self.assertEqual(self._sot.capabilities.version, FirmwareVersion(0, 11, 0))

    def test_get_sampling_rate(self):
        self.do_setup()

        ftr = self._submit_req_resp_handler(1, b"\xff\x04\x40\x00")
        r = self._sot.get_sampling_rate()

        self.assertEqual(ftr.result(), b"\x03")
        self.assertEqual(r, 512.0)

    def test_get_data_types(self):
        self.do_setup()

        ftr = self._submit_req_resp_handler(
            1, b"\xff\x02\x40\x00\x01\xff\x01\x09\x01\x01\x12"
        )
        r = self._sot.get_data_types()

        self.assertEqual(ftr.result(), b"\x01")
        self.assertEqual(r, [EChannelType.TIMESTAMP, EChannelType.INTERNAL_ADC_A1])

    def test_streaming(self):
        self.do_setup()

        pkts = []

        def pkt_handler(new_pkt: DataPacket) -> None:
            pkts.append(new_pkt)

        inquiry_ftr = self._submit_req_resp_handler(
            1, b"\xff\x02\x40\x00\x01\xff\x01\x09\x01\x01\x12"
        )
        start_streaming_ftr = self._submit_req_resp_handler(1, b"\xff")
        self._submit_req_resp_handler(0, b"\x00\x25\x13\xf4\x4a\x07")
        stop_streaming_ftr = self._submit_req_resp_handler(1, b"\xff")

        self._sot.add_stream_callback(pkt_handler)
        self._sot.start_streaming()

        self.assertEqual(inquiry_ftr.result(), b"\x01")
        self.assertEqual(start_streaming_ftr.result(), b"\x07")

        self._sot.stop_streaming()
        self.assertEqual(stop_streaming_ftr.result(), b"\x20")

        self.assertEqual(len(pkts), 1)
        pkt = pkts[0]

        self.assertEqual(pkt[EChannelType.TIMESTAMP], 15995685)
        self.assertEqual(pkt[EChannelType.INTERNAL_ADC_A1], 1866)

    def test_status_update(self):
        self.do_setup()

        pkts = []

        def status_handler(new_pkt: list[bool]) -> None:
            pkts.append(new_pkt)

        self._sot.add_status_callback(status_handler)

        self._submit_req_resp_handler(1, b"\x8a\x71\x20\xff\x7a\x03ABC")
        r = self._sot.get_device_name()
        self.assertEqual(r, "ABC")

        self.assertEqual(len(pkts), 1)
        pkt = pkts[0]

        self.assertEqual(pkt, [False, False, False, False, False, True, False, False])

    def test_get_firmware_version(self):
        self.do_setup()

        self._submit_req_resp_handler(1, b"\xff\x2f\x03\x00\x01\x00\x02\x03")
        fwtype, fwver = self._sot.get_firmware_version()

        self.assertEqual(fwtype, EFirmwareType.LogAndStream)
        self.assertEqual(fwver, FirmwareVersion(1, 2, 3))

    def test_get_hardware_version(self):
        self.do_setup()

        self._submit_req_resp_handler(1, b"\xff\x25\x03")
        hw_version = self._sot.get_device_hardware_version()
        self.assertEqual(hw_version, HardwareVersion.SHIMMER3)

        self._submit_req_resp_handler(1, b"\xff\x25\x0a")
        hw_version = self._sot.get_device_hardware_version()
        self.assertEqual(hw_version, HardwareVersion.SHIMMER3R)

        self._submit_req_resp_handler(1, b"\xff\x25\x04")
        hw_version = self._sot.get_device_hardware_version()
        self.assertEqual(hw_version, HardwareVersion.UNKNOWN)

    def test_status_ack_disable(self):
        self.do_setup(initialize=False)

        # Queue response for version command
        self._submit_req_resp_handler(1, b"\xff\x2f\x03\x00\x00\x00\x0f\x04")
        self._submit_req_resp_handler(1, b"\xff\x25\x03")
        # Queue response for disabling the status acknowledgment
        req_future = self._submit_req_resp_handler(2, b"\xff")

        self._sot.initialize()
        req_data = req_future.result()
        self.assertEqual(req_data, b"\xa3\x00")

    def test_status_ack_not_disable(self):
        self.do_setup(initialize=False, disable_status_ack=False)

        # Queue response for version command
        self._submit_req_resp_handler(1, b"\xff\x2f\x03\x00\x00\x00\x0f\x04")
        self._submit_req_resp_handler(1, b"\xff\x25\x03")
        self._sot.initialize()
