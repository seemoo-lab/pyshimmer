from typing import Tuple
from unittest import TestCase

from pyshimmer.bluetooth.bt_commands import ShimmerCommand, GetSamplingRateCommand, GetConfigTimeCommand, \
    SetConfigTimeCommand, GetRealTimeClockCommand, SetRealTimeClockCommand, GetStatusCommand, GetFirmwareVersionCommand, \
    InquiryCommand, StartStreamingCommand, StopStreamingCommand, StartLoggingCommand, StopLoggingCommand, \
    GetEXGRegsCommand, SetEXGRegsCommand, GetExperimentIDCommand, SetExperimentIDCommand, GetDeviceNameCommand, \
    SetDeviceNameCommand, DummyCommand, DataPacket
from pyshimmer.bluetooth.bt_serial import BluetoothSerial
from pyshimmer.device import EFirmwareType, EChannelType, ChDataTypeAssignment
from pyshimmer.test_util import MockSerial


class BluetoothCommandsTest(TestCase):

    @staticmethod
    def create_mock() -> Tuple[BluetoothSerial, MockSerial]:
        mock = MockSerial()
        # noinspection PyTypeChecker
        serial = BluetoothSerial(mock)
        return serial, mock

    def assert_cmd(self, cmd: ShimmerCommand, req_data: bytes,
                   resp_code: int = None, resp_data: bytes = None, exp_result: any = None) -> any:
        serial, mock = self.create_mock()

        cmd.send(serial)
        actual_req_data = mock.test_get_write_data()
        self.assertEqual(actual_req_data, req_data)

        if resp_code is None:
            self.assertFalse(cmd.has_response())
            return None

        self.assertTrue(cmd.has_response())
        self.assertEqual(cmd.get_response_code(), resp_code)

        mock.test_put_read_data(resp_data)

        act_result = cmd.receive(serial)
        if exp_result is not None:
            self.assertEqual(act_result, exp_result)
        return act_result

    def test_get_sampling_rate_command(self):
        cmd = GetSamplingRateCommand()
        self.assert_cmd(cmd, b'\x03', 0x04, b'\x04\x40\x00', 512.0)

    def test_get_config_time_command(self):
        cmd = GetConfigTimeCommand()
        self.assert_cmd(cmd, b'\x87', 0x86, b'\x86\x02\x34\x32', 42)

    def test_set_config_time_command(self):
        cmd = SetConfigTimeCommand(43)
        self.assert_cmd(cmd, b'\x85\x02\x34\x33')

    def test_get_rtc(self):
        cmd = GetRealTimeClockCommand()
        r = self.assert_cmd(cmd, b'\x91', 0x90, b'\x90\x1f\xb1\x93\x09\x00\x00\x00\x00')
        self.assertAlmostEqual(r, 4903.3837585)

    def test_set_rtc(self):
        cmd = SetRealTimeClockCommand(10)
        self.assert_cmd(cmd, b'\x8f\x00\x00\x05\x00\x00\x00\x00\x00')

    def test_get_status_command(self):
        cmd = GetStatusCommand()
        self.assert_cmd(cmd, b'\x72', 0x8a, b'\x8a\x71\x25', [True, False, True, False, False, True, False, False])

    def test_get_firmware_version_command(self):
        cmd = GetFirmwareVersionCommand()
        type, major, minor, patch = self.assert_cmd(cmd, b'\x2e', 0x2f, b'\x2f\x03\x00\x00\x00\x0b\x00')
        self.assertEqual(type, EFirmwareType.LogAndStream)
        self.assertEqual(major, 0)
        self.assertEqual(minor, 11)
        self.assertEqual(patch, 0)

    def test_inquiry_command(self):
        cmd = InquiryCommand()
        sr, buf_size, ctypes = self.assert_cmd(cmd, b'\x01', 0x02, b'\x02\x40\x00\x01\xff\x01\x09\x01\x01\x12')

        self.assertEqual(sr, 512.0)
        self.assertEqual(buf_size, 1)
        self.assertEqual(ctypes, [EChannelType.INTERNAL_ADC_13])

    def test_start_streaming_command(self):
        cmd = StartStreamingCommand()
        self.assert_cmd(cmd, b'\x07')

    def test_stop_streaming_command(self):
        cmd = StopStreamingCommand()
        self.assert_cmd(cmd, b'\x20')

    def test_start_logging_command(self):
        cmd = StartLoggingCommand()
        self.assert_cmd(cmd, b'\x92')

    def test_stop_logging_command(self):
        cmd = StopLoggingCommand()
        self.assert_cmd(cmd, b'\x93')

    def test_get_exg_register_command(self):
        cmd = GetEXGRegsCommand(1)
        r = self.assert_cmd(cmd, b'\x63\x01\x00\x0a', 0x62, b'\x62\x0a\x00\x80\x10\x00\x00\x00\x00\x00\x02\x01')
        self.assertEqual(r.binary, b'\x00\x80\x10\x00\x00\x00\x00\x00\x02\x01')

    def test_get_exg_reg_fail(self):
        serial, mock = self.create_mock()
        cmd = GetEXGRegsCommand(1)

        mock.test_put_read_data(b'\x62\x04\x01\x02\x03\x04')
        self.assertRaises(ValueError, cmd.receive, serial)

    def test_set_exg_register_command(self):
        cmd = SetEXGRegsCommand(1, 0x02, b'\x10\x00')
        self.assert_cmd(cmd, b'\x61\x01\x02\x02\x10\x00')

    def test_get_experiment_id_command(self):
        cmd = GetExperimentIDCommand()
        self.assert_cmd(cmd, b'\x7e', 0x7d, b'\x7d\x06a_test', 'a_test')

    def test_set_experiment_id_command(self):
        cmd = SetExperimentIDCommand('A_Test')
        self.assert_cmd(cmd, b'\x7c\x06A_Test')

    def test_get_device_name_command(self):
        cmd = GetDeviceNameCommand()
        self.assert_cmd(cmd, b'\x7b', 0x7a, b'\x7a\x05S_PPG', 'S_PPG')

    def test_set_device_name_command(self):
        cmd = SetDeviceNameCommand('S_PPG')
        self.assert_cmd(cmd, b'\x79\x05S_PPG')

    def test_dummy_command(self):
        cmd = DummyCommand()
        self.assert_cmd(cmd, b'\x96')

    def test_data_packet(self):
        serial, mock = self.create_mock()

        channels = [EChannelType.TIMESTAMP, EChannelType.INTERNAL_ADC_13]
        data_types = [ChDataTypeAssignment[c] for c in channels]
        ch_and_types = list(zip(channels, data_types))

        pkt = DataPacket(ch_and_types)
        self.assertEqual(pkt.channels, channels)
        self.assertEqual(pkt.channel_types, data_types)

        mock.test_put_read_data(b'\x00\xde\xd0\xb2\x26\x07')
        pkt.receive(serial)

        self.assertEqual(pkt[EChannelType.TIMESTAMP], 0xb2d0de)
        self.assertEqual(pkt[EChannelType.INTERNAL_ADC_13], 0x0726)
