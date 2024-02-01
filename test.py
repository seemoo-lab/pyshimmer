import time

from serial import Serial

from pyshimmer import ShimmerBluetooth, DEFAULT_BAUDRATE, DataPacket, EChannelType


def handler(pkt: DataPacket) -> None:
    cur_value = pkt[EChannelType.INTERNAL_ADC_13]
    print(f'Received new data point: {cur_value}')


if __name__ == '__main__':
    serial = Serial('/dev/rfcomm42', DEFAULT_BAUDRATE)
    shim_dev = ShimmerBluetooth(serial)

    shim_dev.initialize()

    dev_name = shim_dev.get_device_name()
    print(f'My name is: {dev_name}')

    shim_dev.add_stream_callback(handler)

    shim_dev.start_streaming()
    time.sleep(5.0)
    shim_dev.stop_streaming()

    shim_dev.shutdown()