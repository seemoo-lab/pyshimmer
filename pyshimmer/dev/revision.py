from collections.abc import Iterable
from pyshimmer.dev.channels import EChannelType, ChannelDataType, ESensorGroup

from abc import ABC, abstractmethod
from typing import overload
import numpy as np


class HardwareRevision(ABC):

    @abstractmethod
    def sr2dr(self, sr: float) -> int:
        """Calculate equivalent device-specific rate for a sample rate in Hz

        Device-specific sample rates are given in absolute clock ticks per unit of time.
        This function can be used to calculate such a rate for the Shimmer3.

        :param sr: The sampling rate in Hz
        :return: An integer which represents the equivalent device-specific sampling rate
        """
        pass

    @abstractmethod
    def dr2sr(self, dr: int) -> float:
        """Calculate equivalent sampling rate for a given device-specific rate

        Device-specific sample rates are given in absolute clock ticks per unit of time.
        This function can be used to calculate a regular sampling rate in Hz from such a
        rate.

        :param dr: The absolute device rate as integer
        :return: A floating-point number that represents the sampling rate in Hz
        """
        pass

    @overload
    def sec2ticks(self, t_sec: float) -> int: ...

    @overload
    def sec2ticks(self, t_sec: np.ndarray) -> np.ndarray: ...

    @abstractmethod
    def sec2ticks(self, t_sec: float | np.ndarray) -> int | np.ndarray:
        """Calculate equivalent device clock ticks for a time in seconds

        Args:
            t_sec: A time in seconds
        Returns:
            An integer which represents the equivalent number of clock ticks
        """
        pass

    @overload
    def ticks2sec(self, t_ticks: int) -> float: ...

    @overload
    def ticks2sec(self, t_ticks: np.ndarray) -> np.ndarray: ...

    @abstractmethod
    def ticks2sec(self, t_ticks: int | np.ndarray) -> float | np.ndarray:
        """Calculate the time in seconds equivalent to a device clock ticks count

        Args:
            t_ticks: A clock tick counter for which to calculate the time in seconds
        Returns:
            A floating point time in seconds that is equivalent to the number of clock ticks
        """
        pass

    def get_channel_dtype(self, channel: EChannelType) -> ChannelDataType:
        """

        :param channel:
        :return: A list of channel data types with the same order
        """
        pass

    @abstractmethod
    def get_channel_dtypes(
        self, channels: Iterable[EChannelType]
    ) -> list[ChannelDataType]:
        """Return the channel data types for a set of channels

        :param channels: A list of channels
        :return: A list of channel data types with the same order
        """
        pass

    @abstractmethod
    def get_enabled_channels(
        self, sensors: Iterable[ESensorGroup]
    ) -> list[EChannelType]:
        """Determine the set of data channels for a set of enabled sensors

        There exists a one-to-many mapping between enabled sensors and their corresponding
        data channels. This function determines the set of necessary channels for a given
        set of enabled sensors.

        :param sensors: A list of sensors that are enabled on a Shimmer
        :return: A list of channels in the corresponding order
        """
        pass

    @abstractmethod
    def sensors2bitfield(self, sensors: Iterable[ESensorGroup]) -> int:
        """Convert an iterable of sensors into the corresponding bitfield transmitted to
        the Shimmer

        :param sensors: A list of active sensors
        :return: A bitfield that conveys the set of active sensors to the Shimmer
        """
        pass

    @abstractmethod
    def bitfield2sensors(self, bitfield: int) -> list[ESensorGroup]:
        """Decode a bitfield returned from the Shimmer to a list of active sensors

        :param bitfield: The bitfield received from the Shimmer encoding the active sensors
        :return: The corresponding list of active sensors
        """
        pass

    @abstractmethod
    def serialize_sensorlist(self, sensors: Iterable[ESensorGroup]) -> bytes:
        """Serialize a list of sensors to the three-byte bitfield accepted by the Shimmer

        :param sensors: The list of sensors
        :return: A byte string with length 3 that encodes the sensors
        """
        pass

    @abstractmethod
    def deserialize_sensorlist(self, bitfield_bin: bytes) -> list[ESensorGroup]:
        """Deserialize the list of active sensors from the three-byte input received from
        the Shimmer

        :param bitfield_bin: The input bitfield as byte string with length 3
        :return: The list of active sensors
        """
        pass

    @abstractmethod
    def sort_sensors(self, sensors: Iterable[ESensorGroup]) -> list[ESensorGroup]:
        """Sorts the sensors in the list according to the sensor order

        This function is useful to determine the order in which sensor data will appear in
        a data file by ordering the list of sensors according to their order in the file.

        :param sensors: An unsorted list of sensors
        :return: A list with the same sensors as content but sorted according to their
            appearance order in the data file
        """
        pass
