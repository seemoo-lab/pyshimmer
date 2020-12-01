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
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Optional, BinaryIO, List, Callable
from unittest import TestCase

from pyshimmer.bluetooth.bt_api import BluetoothRequestHandler, ShimmerBluetooth
from pyshimmer.bluetooth.bt_commands import GetDeviceNameCommand, SetDeviceNameCommand, DataPacket, GetStatusCommand, \
    GetStringCommand
from pyshimmer.bluetooth.bt_serial import BluetoothSerial
from pyshimmer.device import ChDataTypeAssignment, EChannelType
from pyshimmer.test_util import PTYSerialMockCreator


class BluetoothRequestHandlerTest(TestCase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._mock_creator: Optional[PTYSerialMockCreator] = None
        self._sot: Optional[BluetoothRequestHandler] = None

        self._master: Optional[BinaryIO] = None

    def setUp(self) -> None:
        self._mock_creator = PTYSerialMockCreator()
        serial, self._master = self._mock_creator.create_mock()

        bt_serial = BluetoothSerial(serial)
        self._sot = BluetoothRequestHandler(bt_serial)

    def read_from_master(self, n: int) -> bytes:
        result = bytes()
        while len(result) < n:
            result += self._master.read(n - len(result))

        return result

    def tearDown(self) -> None:
        self._mock_creator.close()

    def test_add_remove_cb(self):
        def cb(_):
            pass

        self._sot.add_stream_callback(cb)
        self._sot.remove_stream_callback(cb)

    def test_enque_command(self):
        cmd = GetDeviceNameCommand()
        compl, resp = self._sot.queue_command(cmd)

        self.assertFalse(compl.has_completed())
        self.assertFalse(resp.has_result())

        r = self.read_from_master(1)
        self.assertEqual(r, b'\x7b')

        self._master.write(b'\xff')
        self._sot.process_single_input_event()

        self.assertTrue(compl.has_completed())
        self.assertFalse(resp.has_result())

        self._master.write(b'\x7a\x05\x53\x5f\x50\x50\x47')
        self._sot.process_single_input_event()

        self.assertTrue(resp.has_result())
        self.assertEqual(resp.get_result(), 'S_PPG')

    def test_enqueue_multibyte_fail(self):
        cmd = GetStringCommand(0x10, b'\x0a\x0b')
        self._sot.queue_command(cmd)

        r = self.read_from_master(1)
        self.assertEqual(r, b'\x10')

        self._master.write(b'\xff')
        self._sot.process_single_input_event()

        self._master.write(b'\x0a\x0b\x02ab')
        self.assertRaises(ValueError, self._sot.process_single_input_event)

    def test_queue_command_no_resp(self):
        cmd = SetDeviceNameCommand('S_PPG')
        compl, resp = self._sot.queue_command(cmd)

        self.assertFalse(compl.has_completed())
        self.assertEqual(resp, None)

        r = self.read_from_master(7)
        self.assertEqual(r, b'\x79\x05S_PPG')

        self._master.write(b'\xff')
        self._sot.process_single_input_event()
        self.assertTrue(compl.has_completed())

    def test_get_status_command(self):
        cmd = GetStatusCommand()
        compl, resp = self._sot.queue_command(cmd)

        self.assertFalse(compl.has_completed())
        self.assertFalse(resp.has_result())

        r = self.read_from_master(1)
        self.assertEqual(r, b'\x72')

        self._master.write(b'\xff\x8a\x71\x21')
        self._sot.process_single_input_event()
        self.assertTrue(compl.has_completed())
        self.assertFalse(resp.has_result())

        self._sot.process_single_input_event()
        self.assertTrue(resp.has_result())
        self.assertEqual(resp.get_result(), [True, False, False, False, False, True, False, False])

    def test_incorrect_resp_code_fail(self):
        cmd = GetDeviceNameCommand()
        _ = self._sot.queue_command(cmd)

        self._master.write(b'\xff\xfe')
        self._sot.process_single_input_event()
        self.assertRaises(ValueError, self._sot.process_single_input_event)

    def test_data_packet(self):
        results: List[DataPacket] = []

        data_pkt_1 = b'\x00\xde\xd0\xb2\x26\x07'
        data_pkt_2 = b'\x00\x1e\xd1\xb2\xfc\x06'

        ch_types = [EChannelType.TIMESTAMP, EChannelType.INTERNAL_ADC_13]
        self._sot.set_stream_types([(c, ChDataTypeAssignment[c]) for c in ch_types])
        self._sot.add_stream_callback(lambda x: results.append(x))

        self._master.write(data_pkt_1)
        self._master.write(data_pkt_2)

        self._sot.process_single_input_event()
        self.assertEqual(len(results), 1)
        pkt = results[0]

        self.assertEqual(pkt.channels, ch_types)
        self.assertEqual(pkt[EChannelType.TIMESTAMP], 0xb2d0de)
        self.assertEqual(pkt[EChannelType.INTERNAL_ADC_13], 0x0726)

        self._sot.process_single_input_event()
        self.assertEqual(len(results), 2)
        pkt = results[1]

        self.assertEqual(pkt.channels, ch_types)
        self.assertEqual(pkt[EChannelType.TIMESTAMP], 0xb2d11e)
        self.assertEqual(pkt[EChannelType.INTERNAL_ADC_13], 0x06fc)

    def test_clear_queues(self):
        cmd = GetDeviceNameCommand()

        compl, resp = self._sot.queue_command(cmd)

        self.assertFalse(compl.has_completed())
        self.assertFalse(resp.has_result())

        self._sot.clear_queues()
        self.assertTrue(compl.has_completed())
        self.assertTrue(resp.has_result())
        self.assertEqual(resp.get_result(), None)


class ShimmerBluetoothIntegrationTest(TestCase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._executor = ThreadPoolExecutor(max_workers=1)

        self._mock_creator: Optional[PTYSerialMockCreator] = None
        self._sot: Optional[ShimmerBluetooth] = None

        self._master: Optional[BinaryIO] = None

    def _submit_handler_fn(self, fn: Callable[[BinaryIO, ShimmerBluetooth], any]) -> Future:
        return self._executor.submit(fn, self._master, self._sot)

    def _submit_req_resp_handler(self, req_len: int, resp: bytes) -> Future:
        def master_fn(master: BinaryIO, _) -> bytes:
            req = bytes()
            while len(req) < req_len:
                req += master.read(req_len - len(req))

            master.write(resp)
            return req

        return self._submit_handler_fn(master_fn)

    def setUp(self) -> None:
        self._mock_creator = PTYSerialMockCreator()
        serial, self._master = self._mock_creator.create_mock()

        self._sot = ShimmerBluetooth(serial)
        self._sot.initialize()

    def tearDown(self) -> None:
        self._sot.shutdown()
        self._mock_creator.close()

    # noinspection PyMethodMayBeStatic
    def test_context_manager(self):
        mock_creator = PTYSerialMockCreator()
        serial, master = mock_creator.create_mock()

        sot = ShimmerBluetooth(serial)
        with sot:
            pass

        mock_creator.close()

    def test_get_sampling_rate(self):
        ftr = self._submit_req_resp_handler(1, b'\xff\x04\x40\x00')
        r = self._sot.get_sampling_rate()

        self.assertEqual(ftr.result(), b'\x03')
        self.assertEqual(r, 512.0)

    def test_get_data_types(self):
        ftr = self._submit_req_resp_handler(1, b'\xff\x02\x40\x00\x01\xff\x01\x09\x01\x01\x12')
        r = self._sot.get_data_types()

        self.assertEqual(ftr.result(), b'\x01')
        self.assertEqual(r, [EChannelType.TIMESTAMP, EChannelType.INTERNAL_ADC_13])

    def test_streaming(self):
        pkts = []

        def pkt_handler(new_pkt: DataPacket) -> None:
            pkts.append(new_pkt)

        inquiry_ftr = self._submit_req_resp_handler(1, b'\xff\x02\x40\x00\x01\xff\x01\x09\x01\x01\x12')
        start_streaming_ftr = self._submit_req_resp_handler(1, b'\xff')
        self._submit_req_resp_handler(0, b'\x00\x25\x13\xf4\x4a\x07')
        stop_streaming_ftr = self._submit_req_resp_handler(1, b'\xff')

        self._sot.add_stream_callback(pkt_handler)
        self._sot.start_streaming()

        self.assertEqual(inquiry_ftr.result(), b'\x01')
        self.assertEqual(start_streaming_ftr.result(), b'\x07')

        self._sot.stop_streaming()
        self.assertEqual(stop_streaming_ftr.result(), b'\x20')

        self.assertEqual(len(pkts), 1)
        pkt = pkts[0]

        self.assertEqual(pkt[EChannelType.TIMESTAMP], 15995685)
        self.assertEqual(pkt[EChannelType.INTERNAL_ADC_13], 1866)
