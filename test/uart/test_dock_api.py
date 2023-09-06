from typing import Tuple
from unittest import TestCase

from pyshimmer import EFirmwareType, ShimmerDock
from pyshimmer.test_util import MockSerial


class DockAPITest(TestCase):

    @staticmethod
    def create_sot(flush: bool = False) -> Tuple[ShimmerDock, MockSerial]:
        mock = MockSerial()
        # noinspection PyTypeChecker
        dock = ShimmerDock(mock, flush_before_req=flush)

        return dock, mock

    def test_context_manager(self):
        dock, mock = self.create_sot()

        self.assertFalse(mock.test_closed)

        with dock:
            pass

        self.assertTrue(mock.test_closed)

    def test_unknown_start_char(self):
        dock, mock = self.create_sot()

        mock.test_put_read_data(b'\x25')
        self.assertRaises(IOError, dock.get_firmware_version)

    def test_bad_arg_response(self):
        dock, mock = self.create_sot()

        mock.test_put_read_data(b'\x24\xfd')
        self.assertRaises(IOError, dock.get_firmware_version)

    def test_bad_cmd_response(self):
        dock, mock = self.create_sot()

        mock.test_put_read_data(b'\x24\xfc')
        self.assertRaises(IOError, dock.get_firmware_version)

    def test_bad_crc_response(self):
        dock, mock = self.create_sot()

        mock.test_put_read_data(b'\x24\xfe')
        self.assertRaises(IOError, dock.get_firmware_version)

    def test_unexpected_cmd_response(self):
        dock, mock = self.create_sot()

        mock.test_put_read_data(b'\x24\x03')
        self.assertRaises(IOError, dock.get_firmware_version)

    def test_unexpected_component(self):
        dock, mock = self.create_sot()

        mock.test_put_read_data(b'\x24\x02\x02\x02\x00\x98z')
        self.assertRaises(IOError, dock.get_firmware_version)

    def test_unexpected_property(self):
        dock, mock = self.create_sot()

        mock.test_put_read_data(b'\x24\x02\x02\x01\x02\xaaE')
        self.assertRaises(IOError, dock.get_firmware_version)

    def test_get_mac_address(self):
        dock, mock = self.create_sot()

        mock.test_put_read_data(b'\x24\x02\x08\x01\x02\x01\x02\x03\x04\x05\x06N\x87')
        r = dock.get_mac_address()

        self.assertEqual(r, (0x01, 0x02, 0x03, 0x04, 0x05, 0x06))
        self.assertEqual(mock.test_get_write_data(), b'\x24\x03\x02\x01\x02\xfb\xef')

    def test_get_firmware_version(self):
        dock, mock = self.create_sot()

        mock.test_put_read_data(b'\x24\x02\x09\x01\x03\x03\x03\x00\x00\x00\x0b\x00\x14\x33')
        hw_ver, fw_type, major, minor, patch = dock.get_firmware_version()

        self.assertEqual(mock.test_get_write_data(), b'\x24\x03\x02\x01\x03\xca\xdc')

        self.assertEqual(hw_ver, 3)
        self.assertEqual(fw_type, EFirmwareType.LogAndStream)
        self.assertEqual(major, 0)
        self.assertEqual(minor, 11)
        self.assertEqual(patch, 0)

    def test_set_rtc(self):
        dock, mock = self.create_sot()

        mock.test_put_read_data(b'\x24\xff\xd9\xb2')
        dock.set_rtc(1.0)

        wd = mock.test_get_write_data()
        self.assertEqual(wd, b'\x24\x01\x0a\x01\x04\x00\x80\x00\x00\x00\x00\x00\x00\x1c\xd2')

    def test_get_rtc(self):
        dock, mock = self.create_sot()

        mock.test_put_read_data(b'\x24\x02\x0a\x01\x05\x9d\x3d\x0d\x00\x00\x00\x00\x00\xb0\xc7')
        r = dock.get_rtc()
        self.assertAlmostEqual(r, 26.481353759765625)

    def test_get_config_rtc(self):
        dock, mock = self.create_sot()

        mock.test_put_read_data(b'\x24\x02\x0a\x01\x04\x00\x00\x15\x00\x00\x00\x00\x00\xe4\xae')
        r = dock.get_config_rtc()
        self.assertEqual(r, 42.0)

        wd = mock.test_get_write_data()
        self.assertEqual(wd, b'\x24\x03\x02\x01\x04\x5d\x45')

    def test_get_exg_register(self):
        dock, mock = self.create_sot()

        # Due to the firmware bug, we first need to emulate the call to set the DAUGHTER_CARD CARD_ID
        mock.test_put_read_data(b'\x24\x02\x02\x03\x02\xca\x2b')
        exp_send_data1 = b'\x24\x03\x05\x03\x02\x00\x00\x00\x3a\xd2'

        # Then the actual call to retrieve the infomem data
        mock.test_put_read_data(b'\x24\x02\x0c\x01\x06\x00\x80\x10\x00\x00\x00\x00\x00\x02\x01\xff\x40')
        exp_send_data2 = b'\x24\x03\x05\x01\x06\x0a\x0a\x00\x42\x74'

        r = dock.get_exg_register(0)

        wd = mock.test_get_write_data()
        self.assertEqual(wd, exp_send_data1 + exp_send_data2)

        self.assertEqual(r.binary, b'\x00\x80\x10\x00\x00\x00\x00\x00\x02\x01')

    def test_get_exg_register_fail(self):
        dock, mock = self.create_sot()

        self.assertRaises(ValueError, dock.get_exg_register, -1)
