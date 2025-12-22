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
from pyshimmer.dev.channels import ChDataTypeAssignment, EChannelType, ChannelDataType
from pyshimmer.dev.fw_version import FirmwareVersion, EFirmwareType
from pyshimmer.dev.revisions import (
    HardwareVersion,
    HardwareRevision,
    HW_REVISIONS,
    REV_SHIMMER3,
    Shimmer3Revision,
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

    def test_stream_types(self, sot: BluetoothRequestHandler):
        assert sot.stream_types == []

        sot.stream_types = [
            (EChannelType.TIMESTAMP, ChannelDataType(4, signed=False, le=True))
        ]
        assert len(sot.stream_types) == 1
        assert sot.stream_types[0][0] == EChannelType.TIMESTAMP

    def test_revision(self, sot: BluetoothRequestHandler, revision: HardwareRevision):
        assert sot.hardware_revision is revision
        new_revision = Shimmer3Revision()

        sot.hardware_revision = new_revision
        assert sot.hardware_revision is new_revision

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


class IntegrationTestHelper:

    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.mock_creator = PTYSerialMockCreator()
        self.sot: ShimmerBluetooth | None = None

    def submit_handler_fn(
        self, fn: Callable[[BinaryIO, ShimmerBluetooth], any]
    ) -> Future:
        return self.executor.submit(fn, self.mock_creator.master_fobj, self.sot)

    def submit_req_resp_handler(self, req_len: int, resp: bytes) -> Future:
        def master_fn(master: BinaryIO, _) -> bytes:
            req = bytes()
            while len(req) < req_len:
                req += master.read(req_len - len(req))

            master.write(resp)
            return req

        return self.submit_handler_fn(master_fn)

    def queue_initialization_data(
        self, version: HardwareVersion | int
    ) -> tuple[Future, Future]:
        # The Bluetooth API automatically requests the firmware version upon
        # initialization. We must prepare a proper response beforehand.
        req_future_fw = self.submit_req_resp_handler(
            req_len=1, resp=b"\xff\x2f\x03\x00\x00\x00\x0b\x00"
        )

        hw_version_bin = version.to_bytes(length=1)
        req_future_hw = self.submit_req_resp_handler(
            req_len=1, resp=b"\xff\x25" + hw_version_bin
        )
        return req_future_fw, req_future_hw

    def execute_sot_initialization(
        self, version: HardwareVersion | int = HardwareVersion.SHIMMER3
    ) -> None:

        req_future_fw, req_future_hw = self.queue_initialization_data(version)

        self.sot.initialize()

        # Check that it properly asked for the firmware version
        result = req_future_fw.result()
        assert result == b"\x2e"
        result = req_future_hw.result()
        assert result == b"\x3f"

    def setup(
        self,
        run_sot_initialize: bool = True,
        hw_version: HardwareVersion | int = HardwareVersion.SHIMMER3,
        **bt_kwargs,
    ):
        self.mock_creator.create_mock()

        self.sot = ShimmerBluetooth(self.mock_creator.slave_serial, **bt_kwargs)

        if run_sot_initialize:
            self.execute_sot_initialization(hw_version)

    def teardown(self):
        self.sot.shutdown()
        self.mock_creator.close()
        self.executor.shutdown(cancel_futures=True)


class TestShimmerBluetoothIntegration:

    @pytest.fixture
    def helper(self) -> IntegrationTestHelper:
        helper = IntegrationTestHelper()

        yield helper

        helper.teardown()

    @pytest.fixture(params=[HardwareVersion.SHIMMER3])
    def hw_version(self, request) -> HardwareVersion:
        return request.param

    def test_properties(self, helper: IntegrationTestHelper):
        helper.setup(run_sot_initialize=True)

        assert helper.sot.hardware_revision == REV_SHIMMER3
        assert helper.sot.hardware_version == HardwareVersion.SHIMMER3
        assert helper.sot.firmware_type == EFirmwareType.LogAndStream
        assert helper.sot.firmware_version == FirmwareVersion(0, 11, 0)

    def test_custom_revision(self, helper: IntegrationTestHelper):
        custom_revision = Shimmer3Revision()

        helper.setup(
            run_sot_initialize=True,
            hw_version=HardwareVersion.SHIMMER3,
            # Set a custom revision
            revision=custom_revision,
        )

        assert helper.sot.hardware_version == HardwareVersion.SHIMMER3
        assert helper.sot.hardware_revision == custom_revision

    def test_error_if_unsupported_version(self, helper: IntegrationTestHelper):
        helper.setup(run_sot_initialize=False)

        helper.queue_initialization_data(version=HardwareVersion.SHIMMER2)

        with pytest.raises(ValueError):
            helper.sot.initialize()

    def test_context_manager(self, helper: IntegrationTestHelper):
        helper.setup(run_sot_initialize=False)

        req_future_fw = helper.submit_req_resp_handler(
            req_len=1, resp=b"\xff\x2f\x03\x00\x00\x00\x0b\x00"
        )
        req_future_hw = helper.submit_req_resp_handler(req_len=1, resp=b"\xff\x25\x03")
        with helper.sot:
            # We check that the API properly asked for the firmware version
            req_data_fw = req_future_fw.result()
            assert req_data_fw == b"\x2e"
            req_data_hw = req_future_hw.result()
            assert req_data_hw == b"\x3f"

            # It should now be in an initialized state
            assert helper.sot.initialized is True

    def test_version_and_capabilities(
        self, helper: IntegrationTestHelper, hw_version: HardwareVersion
    ):
        helper.setup(run_sot_initialize=True, hw_version=hw_version)

        assert helper.sot.initialized is True
        assert helper.sot.capabilities is not None

        assert helper.sot.capabilities.fw_type == EFirmwareType.LogAndStream
        assert helper.sot.capabilities.version == FirmwareVersion(0, 11, 0)

    def test_get_sampling_rate(
        self, helper: IntegrationTestHelper, hw_version: HardwareVersion
    ):
        helper.setup(run_sot_initialize=True, hw_version=hw_version)

        ftr = helper.submit_req_resp_handler(1, b"\xff\x04\x40\x00")
        r = helper.sot.get_sampling_rate()

        assert ftr.result() == b"\x03"
        assert r == 512.0

    def test_get_data_types(
        self, helper: IntegrationTestHelper, hw_version: HardwareVersion
    ):
        helper.setup(run_sot_initialize=True, hw_version=hw_version)

        ftr = helper.submit_req_resp_handler(
            1, b"\xff\x02\x40\x00\x01\xff\x01\x09\x01\x01\x12"
        )
        r = helper.sot.get_data_types()

        assert ftr.result() == b"\x01"
        assert r == [EChannelType.TIMESTAMP, EChannelType.INTERNAL_ADC_A1]

    def test_streaming(
        self, helper: IntegrationTestHelper, hw_version: HardwareVersion
    ):
        helper.setup(run_sot_initialize=True, hw_version=hw_version)

        pkts = []

        def pkt_handler(new_pkt: DataPacket) -> None:
            pkts.append(new_pkt)

        inquiry_ftr = helper.submit_req_resp_handler(
            1, b"\xff\x02\x40\x00\x01\xff\x01\x09\x01\x01\x12"
        )
        start_streaming_ftr = helper.submit_req_resp_handler(1, b"\xff")
        helper.submit_req_resp_handler(0, b"\x00\x25\x13\xf4\x4a\x07")
        stop_streaming_ftr = helper.submit_req_resp_handler(1, b"\xff")

        helper.sot.add_stream_callback(pkt_handler)
        helper.sot.start_streaming()

        assert inquiry_ftr.result() == b"\x01"
        assert start_streaming_ftr.result() == b"\x07"

        helper.sot.stop_streaming()
        assert stop_streaming_ftr.result() == b"\x20"

        assert len(pkts) == 1
        pkt = pkts[0]

        assert pkt[EChannelType.TIMESTAMP] == 15995685
        assert pkt[EChannelType.INTERNAL_ADC_A1] == 1866

    def test_status_update(
        self, helper: IntegrationTestHelper, hw_version: HardwareVersion
    ):
        helper.setup(run_sot_initialize=True, hw_version=hw_version)

        pkts = []

        def status_handler(new_pkt: list[bool]) -> None:
            pkts.append(new_pkt)

        helper.sot.add_status_callback(status_handler)

        helper.submit_req_resp_handler(1, b"\x8a\x71\x20\xff\x7a\x03ABC")
        r = helper.sot.get_device_name()
        assert r == "ABC"

        assert len(pkts) == 1
        pkt = pkts[0]

        assert pkt == [False, False, False, False, False, True, False, False]

    def test_get_firmware_version(
        self, helper: IntegrationTestHelper, hw_version: HardwareVersion
    ):
        helper.setup(run_sot_initialize=True, hw_version=hw_version)

        helper.submit_req_resp_handler(1, b"\xff\x2f\x03\x00\x01\x00\x02\x03")
        fwtype, fwver = helper.sot.get_firmware_version()

        assert fwtype == EFirmwareType.LogAndStream
        assert fwver == FirmwareVersion(1, 2, 3)

    def test_get_hardware_version(self, helper: IntegrationTestHelper):
        helper.setup()

        helper.submit_req_resp_handler(1, b"\xff\x25\x03")
        hw_version = helper.sot.get_device_hardware_version()
        assert hw_version == HardwareVersion.SHIMMER3

        helper.submit_req_resp_handler(1, b"\xff\x25\x0a")
        hw_version = helper.sot.get_device_hardware_version()
        assert hw_version == HardwareVersion.SHIMMER3R

        helper.submit_req_resp_handler(1, b"\xff\x25\x04")
        hw_version = helper.sot.get_device_hardware_version()
        assert hw_version == HardwareVersion.UNKNOWN

    def test_status_ack_disable(
        self, helper: IntegrationTestHelper, hw_version: HardwareVersion
    ):
        helper.setup(run_sot_initialize=False, hw_version=hw_version)

        # Queue response for version command
        helper.submit_req_resp_handler(1, b"\xff\x2f\x03\x00\x00\x00\x0f\x04")
        helper.submit_req_resp_handler(1, b"\xff\x25\x03")
        # Queue response for disabling the status acknowledgment
        req_future = helper.submit_req_resp_handler(2, b"\xff")

        helper.sot.initialize()
        req_data = req_future.result()
        assert req_data == b"\xa3\x00"

    def test_status_ack_not_disable(
        self, helper: IntegrationTestHelper, hw_version: HardwareVersion
    ):
        helper.setup(
            run_sot_initialize=False, hw_version=hw_version, disable_status_ack=False
        )

        # Queue response for version command
        helper.submit_req_resp_handler(1, b"\xff\x2f\x03\x00\x00\x00\x0f\x04")
        helper.submit_req_resp_handler(1, b"\xff\x25\x03")
        helper.sot.initialize()
