# pyshimmer - API for Shimmer sensor devices
# Copyright (C) 2023  Lukas Magel, Manuel Fernandez-Carmona

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

import struct
from typing import List

from pyshimmer.util import fmt_hex


class AllCalibration:

    def __init__(self, reg_bin: bytes):
        self._num_bytes = 84
        self._sensor_bytes = 21
        self._num_sensors = 4

        if len(reg_bin) < self._num_bytes:
            raise ValueError(
                f'All calibration data must have length {self._num_bytes}')

        self._reg_bin = reg_bin

    def __str__(self) -> str:
        def print_sensor(sens_num: int) -> str:
            return f'Sensor {sens_num + 1:2d}\n' + \
                   f'\tOffset bias: {self.get_offset_bias(sens_num)}\n' + \
                   f'\tSensitivity: {self.get_sensitivity(sens_num)}\n' + \
                   f'\tAlignment Matrix: {self.get_ali_mat(sens_num)}\n'

        obj_str = f''
        for i in range(0, self._num_sensors):
            obj_str += print_sensor(i)

        reg_bin_str = fmt_hex(self._reg_bin)
        obj_str += f'Binary: {reg_bin_str}\n'

        return obj_str

    @property
    def binary(self):
        return self._reg_bin
    
    def __eq__(self, other: "AllCalibration") -> bool:
        return self._reg_bin == other._reg_bin

    def _check_sens_num(self, sens_num: int) -> None:
        if not 0 <= sens_num < (self._num_sensors):
            raise ValueError(f'Sensor num must be 0 to {self._num_sensors-1}')

    def get_offset_bias(self, sens_num: int) -> List[int]:
        self._check_sens_num(sens_num)
        start_offset = sens_num * self._sensor_bytes
        end_offset = start_offset + 6
        ans = list(struct.unpack(
            '>hhh', self._reg_bin[start_offset:end_offset]))
        return ans

    def get_sensitivity(self, sens_num: int) -> List[int]:
        self._check_sens_num(sens_num)
        start_offset = sens_num * self._sensor_bytes + 6
        end_offset = start_offset + 6
        ans = list(struct.unpack(
            '>hhh', self._reg_bin[start_offset:end_offset]))
        return ans

    def get_ali_mat(self, sens_num: int) -> List[int]:
        self._check_sens_num(sens_num)
        start_offset = sens_num * self._sensor_bytes + 12
        end_offset = start_offset + 9
        ans = list(struct.unpack(
            '>bbbbbbbbb', self._reg_bin[start_offset:end_offset]))
        return ans
