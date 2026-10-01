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
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import BinaryIO

import numpy as np

from pyshimmer.dev.channels import EChannelType
from pyshimmer.dev.exg import is_exg_ch, get_exg_ch, ExGRegister
from pyshimmer.dev.gsr import calibrate_gsr
from pyshimmer.dev.revisions import HardwareRevision, HardwareVersion
from pyshimmer.reader.binary_reader import ShimmerBinaryReader
from pyshimmer.reader.reader_const import (
    ADC_GAIN,
    ADC_OFFSET,
    ADC_REF_VOLT,
    EXG_ADC_REF_VOLT,
    EXG_ADC_OFFSET,
)
from pyshimmer.util import calibrate_u12_adc_value


def fit_linear_1d(xp, fp, x):
    fit_coef = np.polyfit(xp, fp, 1)
    fn = np.poly1d(fit_coef)
    return fn(x)


class ChannelPostProcessor(ABC):

    @abstractmethod
    def process(
        self, channels: dict[EChannelType, np.ndarray], reader: ShimmerBinaryReader
    ) -> dict[EChannelType, np.ndarray]:
        pass


class SingleChannelProcessor(ChannelPostProcessor, ABC):

    def __init__(self, ch_types: list[EChannelType] = None):
        super().__init__()
        self._ch_types = ch_types

    def process(
        self, channels: dict[EChannelType, np.ndarray], reader: ShimmerBinaryReader
    ) -> dict[EChannelType, np.ndarray]:

        if self._ch_types is None:
            ch_types = list(channels.keys())
        else:
            ch_types = [t for t in self._ch_types if t in channels]

        result = channels.copy()
        for ch_type in ch_types:
            result[ch_type] = self.process_channel(ch_type, channels[ch_type], reader)

        return result

    @abstractmethod
    def process_channel(
        self, ch_type: EChannelType, y: np.ndarray, reader: ShimmerBinaryReader
    ) -> np.ndarray:
        pass


class ExGProcessor(SingleChannelProcessor):

    def __init__(self):
        exg_channels = [t for t in EChannelType if is_exg_ch(t)]
        super().__init__(exg_channels)

    def process_channel(
        self, ch_type: EChannelType, y: np.ndarray, reader: ShimmerBinaryReader
    ) -> np.ndarray:
        chip_id, ch_id = get_exg_ch(ch_type)
        exg_reg = reader.get_exg_reg(chip_id)
        gain = exg_reg.get_ch_gain(ch_id)

        ch_dtype = reader.hardware_revision.get_channel_dtype(ch_type)
        resolution = 8 * ch_dtype.size
        sensitivity = EXG_ADC_REF_VOLT / (2 ** (resolution - 1) - 1)

        # According to formula in Shimmer ECG User Guide
        y_volt = (y - EXG_ADC_OFFSET) * sensitivity / gain
        return y_volt


class PPGProcessor(SingleChannelProcessor):

    def __init__(self):
        super().__init__([EChannelType.INTERNAL_ADC_A1])

    def process_channel(
        self, ch_type: EChannelType, y: np.ndarray, reader: ShimmerBinaryReader
    ) -> np.ndarray:
        # The channel is connected to a 12bit ADC of the microcontroller, so the raw
        # readings are ADC counts which must be scaled to a voltage
        return calibrate_u12_adc_value(
            y, offset=ADC_OFFSET, vRefP=ADC_REF_VOLT, gain=ADC_GAIN
        )


class GSRProcessor(ChannelPostProcessor):
    """Converts the galvanic skin response channel

    The raw channel encodes the active range of the GSR circuit alongside the ADC
    reading. This processor leaves the raw channel untouched and adds the active
    range, the skin resistance in kOhm, and the skin conductance in microsiemens as
    derived channels.
    """

    def process(
        self, channels: dict[EChannelType, np.ndarray], reader: ShimmerBinaryReader
    ) -> dict[EChannelType, np.ndarray]:
        if EChannelType.GSR_RAW not in channels:
            return channels

        gsr_range, resistance, conductance = calibrate_gsr(
            channels[EChannelType.GSR_RAW]
        )

        result = channels.copy()
        result[EChannelType.GSR_RANGE] = gsr_range
        result[EChannelType.GSR_RESISTANCE] = resistance
        result[EChannelType.GSR_CONDUCTANCE] = conductance

        return result


class PressureProcessor(ChannelPostProcessor):
    """Compensates the barometric pressure and temperature channels

    The pressure sensors report two uncompensated ADC readings which must be combined
    with the calibration parameters of the device to obtain a pressure in kPa and a
    temperature in degrees Celsius. If the device did not store any calibration
    parameters, both channels are left untouched.
    """

    def process(
        self, channels: dict[EChannelType, np.ndarray], reader: ShimmerBinaryReader
    ) -> dict[EChannelType, np.ndarray]:
        pressure_channels = [EChannelType.PRESSURE, EChannelType.TEMPERATURE]
        if not all(c in channels for c in pressure_channels):
            return channels

        calib = reader.pressure_calibration
        if calib is None:
            # The device did not store calibration parameters, so the raw readings
            # cannot be converted into physical units
            return channels

        pressure, temperature = calib.calibrate(
            channels[EChannelType.PRESSURE], channels[EChannelType.TEMPERATURE]
        )

        result = channels.copy()
        result[EChannelType.PRESSURE] = pressure
        result[EChannelType.TEMPERATURE] = temperature

        return result


class TriAxCalProcessor(ChannelPostProcessor):

    def process(
        self, channels: dict[EChannelType, np.ndarray], reader: ShimmerBinaryReader
    ) -> dict[EChannelType, np.ndarray]:
        result = channels.copy()
        revision = reader.hardware_revision

        for sensor in revision.triaxcal_sensors:
            if sensor not in reader.enabled_sensors:
                continue

            sensor_channels = revision.get_enabled_channels([sensor])
            if not all(c in channels for c in sensor_channels):
                # The sensor is enabled but its channels were not recorded
                continue

            if not reader.has_triaxcal_params(sensor):
                # The device did not store calibration parameters for the sensor, so
                # its channels are left uncalibrated
                continue

            channel_data = np.stack([channels[c] for c in sensor_channels])
            o, g, a = reader.get_triaxcal_params(sensor)

            g_a = np.matmul(g, a)
            r = np.linalg.solve(g_a, channel_data - o[..., None])

            for i, ch in enumerate(sensor_channels):
                result[ch] = r[i]

        return result


class ShimmerReader:

    def __init__(
        self,
        fp: BinaryIO = None,
        bin_reader: ShimmerBinaryReader = None,
        sync: bool = True,
        post_process: bool = True,
        processors: list[ChannelPostProcessor] = None,
        hw_version: HardwareVersion = None,
    ):
        if fp is not None:
            self._bin_reader = ShimmerBinaryReader(fp, hw_version=hw_version)
        elif bin_reader is not None:
            self._bin_reader = bin_reader
        else:
            raise ValueError(
                "Need to provide file object or binary reader as parameter."
            )

        self._ts = None
        self._ch_samples = {}
        self._sync = sync

        self._pp = post_process
        if processors is not None:
            self._processors = processors
        else:
            self._processors = [
                ExGProcessor(),
                PPGProcessor(),
                TriAxCalProcessor(),
                PressureProcessor(),
                GSRProcessor(),
            ]

    @staticmethod
    def _apply_synchronization(
        data_ts: np.ndarray, offset_index: np.ndarray, offsets: np.ndarray
    ):
        # We discard all synchronization offsets for which we do not possess timestamps.
        index_safe = offset_index[offset_index < len(data_ts)]

        offsets_ts = data_ts[index_safe]
        data_offsets = fit_linear_1d(offsets_ts, offsets, data_ts)

        aligned_ts = data_ts - data_offsets
        return aligned_ts

    def _apply_clock_offsets(self, ts: np.ndarray):
        # First, we need calculate absolute timestamps relative to the boot-up time of
        # the Shimmer. In order to do so, we use the 40bit initial timestamp to
        # calculate an offset to apply to each timestamp.
        boot_offset = self._bin_reader.start_timestamp - ts[0]
        ts_boot = ts + boot_offset

        if self._bin_reader.has_global_clock:
            return ts_boot + self._bin_reader.global_clock_diff
        else:
            return ts_boot

    def _process_signals(
        self, channels: dict[EChannelType, np.ndarray]
    ) -> dict[EChannelType, np.ndarray]:
        result = channels.copy()

        for processor in self._processors:
            result = processor.process(result, self._bin_reader)

        return result

    def load_file_data(self):
        samples, sync_offsets = self._bin_reader.read_data()
        ts_raw = samples.pop(EChannelType.TIMESTAMP)

        ts_unwrapped = self.hardware_revision.unwrap_device_timestamps(ts_raw)
        ts_sane = self._apply_clock_offsets(ts_unwrapped)

        if self._sync and self._bin_reader.has_sync:
            ts_sane = self._apply_synchronization(ts_sane, *sync_offsets)

        if self._pp:
            self._ch_samples = self._process_signals(samples)
        else:
            self._ch_samples = samples

        self._ts = self.hardware_revision.ticks2sec(ts_sane)

    def get_exg_reg(self, chip_id: int) -> ExGRegister:
        return self._bin_reader.get_exg_reg(chip_id)

    def __getitem__(self, item: EChannelType) -> np.ndarray:
        if item == EChannelType.TIMESTAMP:
            return self.timestamp

        return self._ch_samples[item]

    @property
    def hardware_revision(self) -> HardwareRevision:
        return self._bin_reader.hardware_revision

    @property
    def timestamp(self) -> np.ndarray:
        return self._ts

    @property
    def channels(self) -> list[EChannelType]:
        # We return all but the first channel which are the timestamps
        return self._bin_reader.enabled_channels[1:]

    @property
    def derived_channels(self) -> list[EChannelType]:
        """Channels that the post processors calculated from the recorded channels

        These channels are not present in the data file. They are only available if
        post processing is enabled.

        :return: A list of the available derived channels
        """
        recorded = set(self._bin_reader.enabled_channels)
        return [c for c in self._ch_samples if c not in recorded]

    @property
    def sample_rate(self) -> float:
        return self.hardware_revision.dr2sr(self._bin_reader.sample_rate)

    @property
    def exg_reg1(self) -> ExGRegister:
        return self.get_exg_reg(0)

    @property
    def exg_reg2(self) -> ExGRegister:
        return self.get_exg_reg(1)
