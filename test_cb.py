import time

from serial import Serial

from pyshimmer import ShimmerBluetooth, DEFAULT_BAUDRATE, DataPacket, EChannelType

import bluetooth
import subprocess


def search_shimmers():

    print(f'Discovering devices: ') 
    nearby_devices = bluetooth.discover_devices(duration=8, lookup_names=True, flush_cache=True, lookup_class=False)
    print(f'There are  { len(nearby_devices) } bt devices on range')
    shimmer_devs = dict()
    for addr, name in nearby_devices:
        if "Shimmer3" in name:
            shimmer_devs[name] = addr

    print(f'{ len(shimmer_devs) } devices detected:')
    print(shimmer_devs)

def rf_connect(bt_addr, serial_id):
    a = subprocess.run(["rfcomm", "bind", str(serial_id), bt_addr, "6"]) 
    return a

def rf_release(serial_id):
    a = subprocess.run(["rfcomm", "release", str(serial_id)]) 
    return a

def stream_cb(pkt: DataPacket) -> None:   
    print(f'Received new data packet: ') 
    for chan in pkt.channels:
        print(f'channel: ' + str(chan)) 
        print(f'value: ' + str(pkt[chan]))     
    print('') 

def main(args=None):    
    serial = Serial('/dev/rfcomm42', DEFAULT_BAUDRATE)
    shim_dev = ShimmerBluetooth(serial)

    shim_dev.initialize()

    dev_name = shim_dev.get_device_name()
    print(f'My name is: {dev_name}')

    shim_dev.add_stream_callback(stream_cb)

    shim_dev.start_streaming()
    time.sleep(5.0)
    shim_dev.stop_streaming()

    shim_dev.shutdown()


if __name__ == '__main__':
    main()