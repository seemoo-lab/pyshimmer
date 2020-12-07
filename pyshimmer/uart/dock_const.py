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
UART_SET = 0x01
UART_GET = 0x03

UART_RESPONSE = 0x02
UART_ACK_RESPONSE = 0xFF

UART_BAD_CMD_RESPONSE = 0xFc
UART_BAD_ARG_RESPONSE = 0xFD
UART_BAD_CRC_RESPONSE = 0xFE

CRC_INIT = 0xB0CA
START_CHAR = 0x24

UART_COMP_SHIMMER = 0x01
UART_COMP_BAT = 0x02
UART_COMP_DAUGHTER_CARD = 0x03
UART_COMP_D_ACCEL = 0x04
UART_COMP_GSR = 0x05

UART_PROP_ENABLE = 0x00
UART_PROP_SAMPLE_RATE = 0x01
UART_PROP_MAC = 0x02
UART_PROP_VER = 0x03
UART_PROP_RWC_CFG_TIME = 0x04
UART_PROP_CURR_LOCAL_TIME = 0x05
UART_PROP_INFOMEM = 0x06
UART_PROP_CARD_ID = 0x02

UART_INFOMEM_EXG_OFFSET = 0x0A
