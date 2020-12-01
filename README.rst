pyshimmer: Unofficial Python API for Shimmer Sensor devices
===========================================================

.. image:: https://travis-ci.com/seemoo-lab/pyshimmer.svg?branch=master
    :target: https://travis-ci.com/seemoo-lab/pyshimmer

.. contents::

General Information
-------------------

pyshimmer provides a Python API to work with the wearable sensor devices produced by Shimmer_. The API is divided into
three major components:

* The Bluetooth API: An interface to communicate with the Shimmer LogAndStream firmware via Bluetooth
* The UART API: An interface to communicate with the Shimmer while they are placed in a dock
* The Reader API: An interface to read the binary files produced by the Shimmer devices

.. _Shimmer: http://www.shimmersensing.com/

Contributing
------------
All code in this repository was produced as part of my Master thesis. This means that the API is not
complete. Especially the Bluetooth and UART API do not feature all calls supported by the devices. However, the code
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
PPG device.

Create a new udev rule file: :code:`/etc/udev/rules.d/10-shimmer.rules` and add the following contents:

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

You can also find the example file in :code:`conf/udev/10-shimmer.rules.example`. Distinguishing both Shimmer Docks and
tty interfaces is somewhat difficult because the distinguishing attributes are spread across multiple devices in the
USB device tree. The main distinguishing attribute is the serial ID of the dock. This allows to distinguish between the
ECG and the PPG dock. The second step is to check if the bInterfaceNumber of the tty device is 00 (bootloader) or
01 (device UART). Unfortunately, it is not possible to check attributes from different parents in a single rule and we
need to use the Goto action to create an if clause around the bInterfaceNumber.

In the file, you need to replace the
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
