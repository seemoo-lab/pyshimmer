from typing import Optional, BinaryIO, List
from unittest import TestCase

from pyshimmer.bluetooth.bt_api import BluetoothRequestHandler
from pyshimmer.bluetooth.bt_commands import GetDeviceNameCommand, SetDeviceNameCommand, DataPacket
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
