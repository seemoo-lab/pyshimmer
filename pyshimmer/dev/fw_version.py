from enum import Enum, auto


def ensure_firmware_version(func):
    def wrapper(self, other):
        if not isinstance(other, FirmwareVersion):
            return False

        return func(self, other)

    return wrapper


class EFirmwareType(Enum):
    BtStream = auto()
    SDLog = auto()
    LogAndStream = auto()


class FirmwareVersion:

    def __init__(self, major: int, minor: int, rel: int):
        """Represents the version of the Shimmer firmware

        :param major: Major version
        :param minor: Minor version
        :param rel: Patch level
        """
        self.major = major
        self.minor = minor
        self.rel = rel
        self._key = (major, minor, rel)

    @ensure_firmware_version
    def __eq__(self, other: "FirmwareVersion") -> bool:
        return self._key == other._key

    @ensure_firmware_version
    def __gt__(self, other: "FirmwareVersion") -> bool:
        return self._key > other._key

    @ensure_firmware_version
    def __ge__(self, other: "FirmwareVersion") -> bool:
        return self._key >= other._key

    @ensure_firmware_version
    def __lt__(self, other: "FirmwareVersion") -> bool:
        return self._key < other._key

    @ensure_firmware_version
    def __le__(self, other: "FirmwareVersion") -> bool:
        return self._key <= other._key


class FirmwareCapabilities:

    def __init__(self, fw_type: EFirmwareType, version: FirmwareVersion):
        self._fw_type = fw_type
        self._version = version

    @property
    def fw_type(self) -> EFirmwareType:
        return self._fw_type

    @property
    def version(self) -> FirmwareVersion:
        return self._version

    @property
    def supports_ack_disable(self) -> bool:
        return self._fw_type == EFirmwareType.LogAndStream and \
               self._version >= FirmwareVersion(major=0, minor=15, rel=4)


FirmwareTypeValueAssignment = {
    0x01: EFirmwareType.BtStream,
    0x02: EFirmwareType.SDLog,
    0x03: EFirmwareType.LogAndStream,
}


def get_firmware_type(f_type: int) -> EFirmwareType:
    if f_type not in FirmwareTypeValueAssignment:
        raise ValueError(f'Unknown firmware type: 0x{f_type:x}')

    return FirmwareTypeValueAssignment[f_type]