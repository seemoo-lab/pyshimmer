from serial import Serial

from pyshimmer import ShimmerDock, DEFAULT_BAUDRATE, fmt_hex


def main(args=None):    
        serial = Serial('/dev/ttyECGdev', DEFAULT_BAUDRATE)

        print(f'Connecting docker')
        shim_dock = ShimmerDock(serial)

        mac = shim_dock.get_mac_address()
        print(f'Device MAC: {fmt_hex(mac)}')

        shim_dock.close()


if __name__ == '__main__':
    main()        