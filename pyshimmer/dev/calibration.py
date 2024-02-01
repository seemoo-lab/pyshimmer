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
import struct
from enum import Enum
from typing import List, Dict, Tuple

from pyshimmer.util import bit_is_set, fmt_hex
from .channels import EChannelType


class AllCalibration:

    def __init__(self, reg_bin: bytes):
        self.num_bytes = 84
        self.sensor_bytes = 21
        self.num_sensors = 4

        if len(reg_bin) < self.num_bytes:
            raise ValueError('All calibration data must have length ' + self.num_bytes)
        
        self._reg_bin = reg_bin

    def __str__(self) -> str:
        def print_sensor(sens_num: int) -> str:
            return f'Sensor {sens_num + 1:2d}\n' + \
                   f'\tOffset bias: {self.get_offset_bias(sens_num)}\n' + \
                   f'\tSensitivity: {self.get_sensitivity(sens_num)}\n' + \
                   f'\tAlignment Matrix: {self.get_ali_mat(sens_num)}\n'

        obj_str = f''
        for i in range(0,self.num_sensors):
            obj_str += print_sensor(i)

        reg_bin_str = fmt_hex(self._reg_bin)
        obj_str += f'Binary: {reg_bin_str}\n'

        return obj_str

    def __eq__(self, other: "AllCalibration") -> bool:
        return self._reg_bin == other._reg_bin

    def check_sens_num(self,sens_num: int) -> None:
        if not 0 <= sens_num <= (self.num_sensors-1):
            raise ValueError('Sensor num must be 0 to ' + (self.num_sensors-1))

    def get_offset_bias(self, sens_num: int) -> List[int]:
        self.check_sens_num(sens_num)
        ans = list()
        offset = sens_num * self.sensor_bytes 
        for num_i in range(0,3):
            d_i = struct.unpack('>h', self._reg_bin[offset:offset+2])
            offset = offset + 2
            ans.append(d_i[0])
        return ans

    def get_sensitivity(self, sens_num: int) -> List[int]:
        self.check_sens_num(sens_num)
        ans = list()
        offset = sens_num * self.sensor_bytes + 6
        for num_i in range(0,3):
            d_i = struct.unpack('>h', self._reg_bin[offset:offset+2])
            offset = offset + 2
            ans.append(d_i[0])
        return ans

    def get_ali_mat(self, sens_num: int) -> List[int]:
        self.check_sens_num(sens_num)
        ans = list()
        offset = sens_num * self.sensor_bytes + 12
        for num_i in range(0,9):
            d_i = struct.unpack('>b', self._reg_bin[offset:offset+1])
            offset = offset + 1
            ans.append(d_i[0])
        return ans

