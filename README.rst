pyshimmer: Unofficial Python API for Shimmer Sensor devices
===========================================================

.. image:: https://travis-ci.com/seemoo-lab/pyshimmer.svg?branch=master
    :target: https://travis-ci.com/seemoo-lab/pyshimmer

.. image:: https://www.codefactor.io/repository/github/seemoo-lab/pyshimmer/badge/develop
   :target: https://www.codefactor.io/repository/github/seemoo-lab/pyshimmer/overview/develop
   :alt: CodeFactor

.. image:: https://codecov.io/gh/seemoo-lab/pyshimmer/branch/develop/graph/badge.svg?token=EHK1ISJH7Z
    :target: https://codecov.io/gh/seemoo-lab/pyshimmer

.. contents::

General Information
-------------------

pyshimmer provides a Python API to work with the wearable sensor devices produced by Shimmer_. The API is divided into
three major components:

* The Bluetooth API: An interface to communicate with the Shimmer LogAndStream firmware via Bluetooth
* The Dock API: An interface to communicate with the Shimmer while they are placed in a dock
* The Reader API: An interface to read the binary files produced by the Shimmer devices

.. _Shimmer: http://www.shimmersensing.com/

Please note that the following README does not provide a general introduction into the Shimmer devices. For this, please
consult the corresponding `documentation page <http://www.shimmersensing.com/support/wireless-sensor-networks-documentation/>`_
of the vendor and take a closer look at:

* The Shimmer User Manual
* The LogAndStream Manual
* The SDLog Manual

Contributing
------------
All code in this repository was produced as part of my Master thesis. This means that the API is not
complete. Especially the Bluetooth and Dock API do not feature all calls supported by the devices. However, the code
provides a solid foundation to extend it where necessary. Please feel free to make contributions in case the code is
missing required calls.

Installation
------------

The targeted plattform for this library is **Linux**. It has not been tested under other operating systems. In order to
use all aspects of the library, you need to install the package itself, set up the Bluetooth interface, and possibly
configure udev rules to ensure that the device names are consistent.

pyshimmer Package
^^^^^^^^^^^^^^^^^
In order to install the package itself, clone it and use pip to install it:

.. code-block::

    git clone https://github.com/seemoo-lab/pyshimmer.git
    cd pyshimmer
    pip install .

If you want to run the tests, instead install the package with :code:`test` extras:

.. code-block::

    pip install .[test]

You can then run the tests from the repository root by simply issuing:

.. code-block::

    pytest

Shimmer Firmware
^^^^^^^^^^^^^^^^

The vanilla version of the `Shimmer3 firmware <https://github.com/ShimmerResearch/shimmer3>`_ exhibits several
unfixed bugs (see the `issues page <https://github.com/ShimmerResearch/shimmer3/issues>`_ for more information).
Depending on the firmware you intend to use, you will need to compile and run a custom patched version of the firmware.
In the following table, we list the tested firmware versions and their compatibility.

============= ========= ============= ======================================================================
Firmware Type Version   Compatibility Issues
============= ========= ============= ======================================================================
LogAndStream  v0.11.0   Incompatible  - `Issue 7 <https://github.com/ShimmerResearch/shimmer3/issues/7>`_
                                      - `Issue 10 <https://github.com/ShimmerResearch/shimmer3/issues/10>`_
SDLog         v0.19.0   Compatible
============= ========= ============= ======================================================================

If you want to use the *LogAndStream* firmware with the pyshimmer library, you will need to compile and program a
patched version of the firmware. We provide a forked repository which features the necessary fixes
`here <https://github.com/seemoo-lab/shimmer3/>`_. It also contains instructions on how to compile and program the
firwmare.

Creating udev rules for persistent device filenames
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When plugging a Shimmer dock into the host, Linux will detect two new serial interfaces and a block device representing
the internal SD card of the Shimmer:

* :code:`/dev/ttyUSB0` for the serial interface to the bootloader,
* :code:`/dev/tty/USB1` for the serial interface to the device itself,
* :code:`/dev/sdX` for the block device.

When working with multiple docks and devices, keeping track of the names of the serial interfaces can be quite
cumbersome, since udev simply names the devices in the order they are plugged in to the system. You can use udev rules
to assign persistent names to the device files. Note that the rules do not actually match the Shimmer but the dock that
it is located in. **This means that you need to always place the device in its respective dock**.

The following section provides an example of how to handle two Shimmer docks, one of which is an ECG and the other a
PPG device:

Distinguishing the Shimmer booloader and device interfaces based on their udev attributes is somewhat difficult because
the distinguishing attributes are spread across multiple devices in the USB device tree.
We first differentiate between different Shimmer docks based on the serial ID attribute of the dock. This allows us to
distinguish between the ECG and the PPG dock. The second step is to check the bInterfaceNumber of the tty device.
With this check, we determine if the tty file is the bootloader device, i.e. bInterfaceNumber == 00, or the interface
to the Shimmer itself, i.e. bInterfaceNumber == 01. Unfortunately, it is not possible to check attributes from different
parents in a single rule and we need to use the Goto action to create an if clause around the bInterfaceNumber. You can
see the full udev ruleset in the following code snippet:

.. code-block::

    SUBSYSTEMS=="usb" ATTRS{bInterfaceNumber}!="00" GOTO="is_secondary_interface"
    SUBSYSTEM=="tty" ATTRS{idVendor}=="<id_vendor1>" ATTRS{idProduct}=="<id_product1>" ATTRS{serial}=="<id_serial1>" SYMLINK+="ttyPPGbl"
    SUBSYSTEM=="tty" ATTRS{idVendor}=="<id_vendor2>" ATTRS{idProduct}=="<id_product2>" ATTRS{serial}=="<id_serial2>" SYMLINK+="ttyECGbl"
    GOTO="end"

    LABEL="is_secondary_interface"
    SUBSYSTEM=="tty" ATTRS{idVendor}=="<id_vendor1>" ATTRS{idProduct}=="<id_product1>" ATTRS{serial}=="<id_serial1>" SYMLINK+="ttyPPGdev"
    SUBSYSTEM=="tty" ATTRS{idVendor}=="<id_vendor2>" ATTRS{idProduct}=="<id_product2>" ATTRS{serial}=="<id_serial2>" SYMLINK+="ttyECGdev"
    GOTO="end"

    LABEL="end"

You can also find the example file in :code:`conf/udev/10-shimmer.rules.example`.

In order to create a custom ruleset for your devices, create a new udev rule file
:code:`/etc/udev/rules.d/10-shimmer.rules` and add the above contents. In the file, you need to replace the
:code:`<id_vendor1>`, :code:`<id_product1>`, and :code:`<id_serial1>` of the first device, and the :code:`<id_vendor2>`,
:code:`<id_product2>`, and :code:`<id_serial2>` of the second device. You can find the values by scanning the
:code:`dmesg` command after plugging in a Shimmer device. Here is an example:

.. code-block::

    [144366.290357] usb 1-4.3: new full-speed USB device number 34 using xhci_hcd
    [144366.386661] usb 1-4.3: New USB device found, idVendor=<id_vendor>, idProduct=<id_product>, bcdDevice= 5.00
    [144366.386668] usb 1-4.3: New USB device strings: Mfr=1, Product=2, SerialNumber=3
    [144366.386674] usb 1-4.3: Product: SHIMMER DOCK
    [144366.386679] usb 1-4.3: Manufacturer: FTDI
    [144366.386684] usb 1-4.3: SerialNumber: <id_serial>

Save the file and reload the rules for them to take effect:

.. code-block::

    udevadm control --reload-rules && udevadm trigger

You should now have two strongly named device files for each Shimmer dock:

* :code:`/dev/ttyPPGbl` and :code:`/dev/ttyPPGdev` for the PPG Shimmer bootloader and device interfaces,
* :code:`/dev/ttyECGbl` and :code:`/dev/ttyECGdev` for the ECG Shimmer bootloader and device interfaces.

Configuring the Bluetooth Interface
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The library uses a :code:`tty` serial interface to communicate with the Shimmer over Bluetooth. Before you can use the
library, you need to set up the serial channel appropriately. This has only been tested this under Arch Linux, but other
Linux distributions should work as well.

Requirements:

* Functioning Bluetooth stack
* The :code:`rfcomm` commandline tool. For Arch Linux, use the `bluez-rfcomm AUR <https://aur.archlinux.org/packages/bluez-rfcomm/>`_ package
* The :code:`hcitool` commandline tool. For Arch Linux, use the `bluez-hcitool AUR <https://aur.archlinux.org/packages/bluez-hcitool/>`_ package
* A Shimmer device with  :code:`LogAndStream` firmware

Scan for the device the find out its MAC address:

.. code-block::

    hcitool scan

The MAC address of the listed Shimmer device should end with the *BT Radio ID* imprinted on the back of the device.
Next, you can try and ping the device:

.. code-block::

    hcitool name <mac_addr>

The command should complete with the name listed previously during the scan. Now you can pair the device as follows:

.. code-block::

    rfcomm <bind_id> <mac_address>

where :code:`<bind_id>` is an arbitrary integer of your choosing. The command will create a new serial interface node
with the following name: :code:`/dev/rfcomm<bind_id>`.
The file acts as a regular serial device and allows you to communicate with the Shimmer. The file is also used by the
library.

Using the API
-------------

Using the Bluetooth interface
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you want to connect to the Bluetooth interface, use the :code:`ShimmerBluetooth` class. The API only offers blocking
calls.

.. code-block:: python

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

The example shows how to make simple calls and how to use the Bluetooth streaming capabilities of the device.

Using the Dock API
^^^^^^^^^^^^^^^^^^

.. code-block:: python

    from serial import Serial

    from pyshimmer import ShimmerDock, DEFAULT_BAUDRATE, fmt_hex

    if __name__ == '__main__':
        serial = Serial('/dev/ttyPPGdev', DEFAULT_BAUDRATE)
        shim_dock = ShimmerDock(serial)

        mac = shim_dock.get_mac_address()
        print(f'Device MAC: {fmt_hex(mac)}')

        shim_dock.close()

Using the Dock API works very similar to the Bluetooth API. However, it does not require a separate initialization call
because it does not use a background thread to decode incoming messages.

Using the Reader API
^^^^^^^^^^^^^^^^^^^^

.. code-block:: python

    from pyshimmer import ShimmerReader, EChannelType

    if __name__ == '__main__':

        with open('test/reader/resources/ecg.bin', 'rb') as f:
            reader = ShimmerReader(f)

            # Read the file contents into memory
            reader.load_file_data()

            print(f'Available data channels: {reader.channels}')
            print(f'Sampling rate: {reader.sample_rate} Hz')
            print()

            ts = reader[EChannelType.TIMESTAMP]
            ecg_ch1 = reader[EChannelType.EXG_ADS1292R_1_CH1_24BIT]
            assert len(ts) == len(ecg_ch1)

            print(f'Timestamp: {ts.shape}')
            print(f'ECG Channel: {ecg_ch1.shape}')
            print()

            exg_reg = reader.exg_reg1
            print(f'ECG Chip Sampling Rate: {exg_reg.data_rate} Hz')
            print(f'ECG Chip Gain: {exg_reg.ch1_gain}')

If the data was recorded using the :code:`SDLog` firmware and features synchronization information, the API
automatically interpolates the data to the common timestamp information of the master.
