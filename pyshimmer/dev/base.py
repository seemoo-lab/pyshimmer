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
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, unique

DEFAULT_BAUDRATE = 115200


@dataclass(frozen=True)
class ExpansionBoard:
    """Identifies the expansion board that is attached to a Shimmer device

    Shimmer devices report their expansion board as a triple of board id, revision,
    and special revision. The board determines which sensors are fitted to the
    device, so it is needed to interpret some data channels.

    :param board_id: The board id, see EExpansionBoard
    :param rev: The board revision
    :param rev_special: The special board revision
    """

    board_id: int
    rev: int
    rev_special: int

    def is_at_least(self, board_id: int, rev: int, rev_special: int = 0) -> bool:
        """Check if this board is the given board at the given revision or newer

        :param board_id: The board id to compare against
        :param rev: The minimum board revision
        :param rev_special: The minimum special board revision
        :return: True if the board ids match and this revision is not older
        """
        if self.board_id != board_id:
            return False

        return (self.rev, self.rev_special) >= (rev, rev_special)


@unique
class EExpansionBoard(IntEnum):
    """The expansion board ids relevant to the interpretation of data files"""

    SHIMMER3 = 31
    EXG_UNIFIED = 47
    GSR_UNIFIED = 48
    BR_AMP_UNIFIED = 49
    PROTO3_DELUXE = 38
    PROTO3_MINI = 36

    # Written into the file header by firmware that does not record the expansion
    # board details
    LOG_FILE = 255


# A special revision of this value marks any expansion board that is attached to a
# device with the newer set of IMU sensors
EXP_BOARD_NEW_IMU_SPECIAL_REV = 171
