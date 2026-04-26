from __future__ import annotations

import pytest

from pyshimmer import (
    FirmwareType,
    ShimmerDock,
    RevisionRegistry,
    HardwareVersion,
    FirmwareVersion,
)
from pyshimmer.test_util import MockSerial


class TestDockAPI:

    @pytest.fixture(
        scope="function",
        params=[RevisionRegistry.REV_SHIMMER3, RevisionRegistry.REV_SHIMMER3R],
    )
    def sot_and_mock(self, request) -> tuple[ShimmerDock, MockSerial]:
        mock = MockSerial()

        # noinspection PyTypeChecker
        dock = ShimmerDock(mock, flush_before_req=False, revision=request.param)

        return dock, mock

    @pytest.fixture()
    def sot(self, sot_and_mock: tuple[ShimmerDock, MockSerial]) -> ShimmerDock:
        return sot_and_mock[0]

    @pytest.fixture()
    def mock(self, sot_and_mock: tuple[ShimmerDock, MockSerial]) -> MockSerial:
        return sot_and_mock[1]

    def test_context_manager(self, sot: ShimmerDock, mock: MockSerial):

        assert not mock.test_closed

        with sot:
            pass

        assert mock.test_closed

    def test_hw_ver_detection(self):
        mock = MockSerial()

        # Put the response data for a Shimmer3 hardware revision
        mock.test_put_read_data(
            b"\x24\x02\x09\x01\x03\x03\x03\x00\x00\x00\x0b\x00\x14\x33"
        )

        dock = ShimmerDock(mock, flush_before_req=False, revision=None)

        assert dock.revision is RevisionRegistry.REV_SHIMMER3

    def test_unknown_start_char(self, sot: ShimmerDock, mock: MockSerial):
        mock.test_put_read_data(b"\x25")
        with pytest.raises(IOError):
            sot.get_hw_sw_version()

    def test_bad_arg_response(self, sot: ShimmerDock, mock: MockSerial):
        mock.test_put_read_data(b"\x24\xfd")
        with pytest.raises(IOError):
            sot.get_hw_sw_version()

    def test_bad_cmd_response(self, sot: ShimmerDock, mock: MockSerial):
        mock.test_put_read_data(b"\x24\xfc")
        with pytest.raises(IOError):
            sot.get_hw_sw_version()

    def test_bad_crc_response(self, sot: ShimmerDock, mock: MockSerial):
        mock.test_put_read_data(b"\x24\xfe")
        with pytest.raises(IOError):
            sot.get_hw_sw_version()

    def test_unexpected_cmd_response(self, sot: ShimmerDock, mock: MockSerial):
        mock.test_put_read_data(b"\x24\x03")
        with pytest.raises(IOError):
            sot.get_hw_sw_version()

    def test_unexpected_component(self, sot: ShimmerDock, mock: MockSerial):
        mock.test_put_read_data(b"\x24\x02\x02\x02\x00\x98z")
        with pytest.raises(IOError):
            sot.get_hw_sw_version()

    def test_unexpected_property(self, sot: ShimmerDock, mock: MockSerial):
        mock.test_put_read_data(b"\x24\x02\x02\x01\x02\xaaE")
        with pytest.raises(IOError):
            sot.get_hw_sw_version()

    def test_get_mac_address(self, sot: ShimmerDock, mock: MockSerial):
        mock.test_put_read_data(b"\x24\x02\x08\x01\x02\x01\x02\x03\x04\x05\x06N\x87")
        r = sot.get_mac_address()

        assert r == (0x01, 0x02, 0x03, 0x04, 0x05, 0x06)
        assert mock.test_get_write_data() == b"\x24\x03\x02\x01\x02\xfb\xef"

    def test_get_firmware_version(self, sot: ShimmerDock, mock: MockSerial):
        mock.test_put_read_data(
            b"\x24\x02\x09\x01\x03\x03\x03\x00\x00\x00\x0b\x00\x14\x33"
        )
        hw_ver, fw_type, fw_ver = sot.get_hw_sw_version()

        assert mock.test_get_write_data() == b"\x24\x03\x02\x01\x03\xca\xdc"

        assert hw_ver is HardwareVersion.SHIMMER3
        assert fw_type == FirmwareType.LogAndStream
        assert fw_ver == FirmwareVersion(0, 11, 0)

    def test_set_rtc(self, sot: ShimmerDock, mock: MockSerial):
        mock.test_put_read_data(b"\x24\xff\xd9\xb2")
        sot.set_rtc(1.0)

        expected = b"\x24\x01\x0a\x01\x04\x00\x80\x00\x00\x00\x00\x00\x00\x1c\xd2"
        wd = mock.test_get_write_data()
        assert wd == expected

    def test_get_rtc(self, sot: ShimmerDock, mock: MockSerial):
        mock.test_put_read_data(
            b"\x24\x02\x0a\x01\x05\x9d\x3d\x0d\x00\x00\x00\x00\x00\xb0\xc7"
        )
        r = sot.get_rtc()
        assert r == pytest.approx(26.481353759765625)

    def test_get_config_rtc(self, sot: ShimmerDock, mock: MockSerial):
        mock.test_put_read_data(
            b"\x24\x02\x0a\x01\x04\x00\x00\x15\x00\x00\x00\x00\x00\xe4\xae"
        )
        r = sot.get_config_rtc()
        assert r == 42.0

        wd = mock.test_get_write_data()
        assert wd == b"\x24\x03\x02\x01\x04\x5d\x45"

    def test_get_exg_register(self, sot: ShimmerDock, mock: MockSerial):

        # Due to the firmware bug, we first need to emulate the call to set the
        # DAUGHTER_CARD CARD_ID
        mock.test_put_read_data(b"\x24\x02\x02\x03\x02\xca\x2b")
        exp_send_data1 = b"\x24\x03\x05\x03\x02\x00\x00\x00\x3a\xd2"

        # Then the actual call to retrieve the infomem data
        mock.test_put_read_data(
            b"\x24\x02\x0c\x01\x06\x00\x80\x10\x00\x00\x00\x00\x00\x02\x01\xff\x40"
        )
        exp_send_data2 = b"\x24\x03\x05\x01\x06\x0a\x0a\x00\x42\x74"

        r = sot.get_exg_register(0)

        wd = mock.test_get_write_data()
        assert wd == exp_send_data1 + exp_send_data2

        assert r.binary == b"\x00\x80\x10\x00\x00\x00\x00\x00\x02\x01"

    def test_get_exg_register_fail(self, sot: ShimmerDock, mock: MockSerial):
        with pytest.raises(ValueError):
            sot.get_exg_register(-1)
