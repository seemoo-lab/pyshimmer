# pyshimmer - API for Shimmer sensor devices
# Copyright (C) 2023  Lukas Magel

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
import re
from enum import Enum
from typing import List, Dict, Tuple

from pyshimmer.util import bit_is_set, fmt_hex
from .channels import EChannelType


class ExGMux(Enum):
    NORMAL = 0x00
    SHORTED = 0x01
    RLD_MEASURE = 0x02
    MVDD = 0x03
    TEMP_SENSOR = 0x04
    TEST_SIGNAL = 0x05
    RLD_DRP = 0x06
    RLD_DRM = 0x07
    RLD_DRPM = 0x08
    INPUT3 = 0x09
    RESERVED = 0x0A


class ExGRLDLead(Enum):
    RLD1P = 0x01 << 0
    RLD1N = 0x01 << 1
    RLD2P = 0x01 << 2
    RLD2N = 0x01 << 3


class ERLDRef(Enum):
    EXTERNAL = 0x00
    INTERNAL = 0x01


class ExGRegister:
    GAIN_MAP = {
        0: 6, 1: 1, 2: 2, 3: 3, 4: 4, 5: 8, 6: 12,
    }
    DATA_RATE_MAP = {
        0: 125, 1: 250, 2: 500, 3: 1000, 4: 2000, 5: 4000, 6: 8000, 7: -1
    }
    PD_BIT = 0x01 << 7
    RLD_PD_BIT = 0x01 << 5

    def __init__(self, reg_bin: bytes):
        if len(reg_bin) < 10:
            raise ValueError('Binary register content must have length 10')

        self._reg_bin = reg_bin

    def __str__(self) -> str:
        def print_ch(ch_id: int) -> str:
            return f'Channel {ch_id + 1:2d}\n' + \
                   f'\tPowerdown: {self.is_ch_powerdown(ch_id)}\n' + \
                   f'\tGain: {self.get_ch_gain(ch_id):2d}\n' + \
                   f'\tMultiplexer: {self.get_ch_mux(ch_id).name} ({self.get_ch_mux_bin(ch_id):#06b})\n'

        def fmt_rld_channels(ch_names) -> str:
            ch_names = [ch.name for ch in ch_names] if len(ch_names) > 0 else ['None']
            return ', '.join(ch_names)

        reg_bin_str = fmt_hex(self._reg_bin)
        obj_str = f'ExGRegister:\n' + \
                  f'Data Rate: {self.data_rate:4d}\n' + \
                  f'RLD Powerdown: {self.rld_powerdown}\n' + \
                  f'RLD Channels: {fmt_rld_channels(self.rld_channels)}\n' + \
                  f'RLD Reference: {self.rld_ref.name}\n' + \
                  f'Binary: {reg_bin_str}\n'
        obj_str += print_ch(0)
        obj_str += print_ch(1)
        return obj_str

    def __eq__(self, other: "ExGRegister") -> bool:
        return self._reg_bin == other._reg_bin

    @staticmethod
    def check_ch_id(ch_id: int) -> None:
        if not 0 <= ch_id <= 1:
            raise ValueError('Channel ID must be 0 or 1')

    def _get_ch_byte(self, ch_id: int) -> int:
        ch_offset = 3 + ch_id
        return self._reg_bin[ch_offset]

    def _get_rld_byte(self) -> int:
        return self._reg_bin[0x05]

    def get_ch_gain(self, ch_id: int) -> int:
        self.check_ch_id(ch_id)

        ch_byte = self._get_ch_byte(ch_id)
        gain_bin = (ch_byte & 0x70) >> 4

        return self.GAIN_MAP[gain_bin]

    def get_ch_mux_bin(self, ch_id: int) -> int:
        self.check_ch_id(ch_id)

        ch_byte = self._get_ch_byte(ch_id)
        return ch_byte & 0x0F

    def get_ch_mux(self, ch_id: int) -> ExGMux:
        return ExGMux(self.get_ch_mux_bin(ch_id))

    def is_ch_powerdown(self, ch_id: int) -> bool:
        self.check_ch_id(ch_id)

        ch_byte = self._get_ch_byte(ch_id)
        return bit_is_set(ch_byte, self.PD_BIT)

    @property
    def binary(self):
        return self._reg_bin

    @property
    def ch1_gain(self) -> int:
        return self.get_ch_gain(0)

    @property
    def ch2_gain(self) -> int:
        return self.get_ch_gain(1)

    @property
    def ch1_mux(self) -> ExGMux:
        return self.get_ch_mux(0)

    @property
    def ch2_mux(self) -> ExGMux:
        return self.get_ch_mux(1)

    @property
    def ch1_powerdown(self) -> bool:
        return self.is_ch_powerdown(0)

    @property
    def ch2_powerdown(self) -> bool:
        return self.is_ch_powerdown(1)

    @property
    def data_rate(self) -> int:
        dr_bin = self._reg_bin[0] & 0x07
        return self.DATA_RATE_MAP[dr_bin]

    @property
    def rld_powerdown(self) -> bool:
        rld_byte = self._get_rld_byte()
        return not bit_is_set(rld_byte, self.RLD_PD_BIT)

    @property
    def rld_channels(self) -> List[ExGRLDLead]:
        rld_byte = self._get_rld_byte()
        return [ch for ch in ExGRLDLead if bit_is_set(rld_byte, ch.value)]

    @property
    def rld_ref(self) -> ERLDRef:
        ref_byte = self._reg_bin[9]
        rld_ref = (ref_byte >> 1) & 0x01
        return ERLDRef(rld_ref)


ExG_ChType_Chip_Assignment: Dict[EChannelType, Tuple[int, int]] = {
    EChannelType.EXG_ADS1292R_1_CH1_24BIT: (0, 0),
    EChannelType.EXG_ADS1292R_1_CH1_16BIT: (0, 0),

    EChannelType.EXG_ADS1292R_1_CH2_24BIT: (0, 1),
    EChannelType.EXG_ADS1292R_1_CH2_16BIT: (0, 1),

    EChannelType.EXG_ADS1292R_2_CH1_24BIT: (1, 0),
    EChannelType.EXG_ADS1292R_2_CH1_16BIT: (1, 0),

    EChannelType.EXG_ADS1292R_2_CH2_24BIT: (1, 1),
    EChannelType.EXG_ADS1292R_2_CH2_16BIT: (1, 1),
}


def is_exg_ch(ch_type: EChannelType) -> bool:
    """
    Returns true if the signal that this channel type describes was recorded by a ExG chip

    Args:
        ch_type: The EChannelType of the signal

    Returns:
        True if the channel type belongs to the ExG chips, otherwise False
    """
    # This is hacky but protected by unit tests
    regex = re.compile(r'EXG_ADS1292R_\d_CH\d_\d{2}BIT')
    return regex.match(ch_type.name) is not None


def get_exg_ch(ch_type: EChannelType) -> Tuple[int, int]:
    """
    Each ExG Chip EChannelType originates from a specific ExG chip and channel. This function returns a tuple that
    specifices which chip and channel a certain signal EChannelType was recorded with.

    Args:
        ch_type: The EChannelType of the signal

    Returns:
        A tuple of ints which represents the chip id {0, 1} and the channel id {0, 1}.

    """
    return ExG_ChType_Chip_Assignment[ch_type]
