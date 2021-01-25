#
# MCH2021 Badge Platform
#

import os
import time
import subprocess
import binascii

import serial
import serial.tools.list_ports

from nmigen.build import *
from nmigen.vendor.lattice_ice40 import LatticeICE40Platform

from nmigen_boards.resources import *


class MCH2021BadgePrototype1(LatticeICE40Platform):
    """ Platform for 'Prototype 1' MCH2021 Badges. """

    VENDOR_ID  = 0x16d0
    PRODUCT_ID = 0x0f9a

    device  = "iCE40UP5K"
    package = "SG48"

    # For now, use the iCE40's internal oscillator as our default, as it's
    # there no matter what firmware's running on the ESP32.
    #
    # We'll start off with this undivided, at 48MHz.
    #
    default_clk = "SB_HFOSC"
    hfosc_div   = 0

    resources = [

        #
        # Direct I/O
        #

        # "iPane Mini" RBG LED
        RGBLEDResource(0, r="40", g="39", b="41", invert=True, attrs=Attrs(IO_STANDARD="SB_LVCMOS")),

        # LCD screen
        Resource("lcd", 0,
            Subsignal("d",      Pins("26 27 28 31 32 34 35 36", dir="io")),
            Subsignal("rs",     Pins("11",                      dir="o" )),
            Subsignal("wr",     Pins("23",                      dir="o" )),
            Subsignal("enable", Pins("38",                      dir="o" )),
            Subsignal("fmark",  Pins("25",                      dir="i" )),
            Attrs(IO_STANDARD="SB_LVCMOS")
        ),

        # Delta-sigma audio, to TRS jack.
        Resource("audio", 0 ,
            Subsignal("l", Pins("43", dir="o")),
            Subsignal("r", Pins("42", dir="o")),
            Attrs(IO_STANDARD="SB_LVCMOS")
        ),

        # PSRAM
        Resource("spi_psram", 0,
            Subsignal("clk",  Pins("15",          dir="o")),
            Subsignal("d",    Pins("19 12 18 21", dir="io")),
            Subsignal("cs",  PinsN("15",          dir="o")),
            Attrs(IO_STANDARD="SB_LVCMOS")
        ),


        #
        # STM32 Connections
        # 

        # Clock signal from the STM32's oscillator.
        Resource(0, "mcu_clk", Pins("37"), Attrs(IO_STANDARD="SB_LVCMOS")),

        # UART connection to the STM32, and thus to a connected USB host.
        UARTResource(0, rx="6", tx="9", attrs=Attrs(IO_STANDARD="SB_LVCMOS")),

        #
        # ESP32 Connections
        #
        SPIResource(0, clk="15", copi="17", cipo="14", cs="16", role="peripheral",
            attrs=Attrs(IO_STANDARD="SB_LVCMOS")),
        Resource("irq", 0, Pins("10"), Attrs(IO_STANDARD="SB_LVCMOS")),

    ]

    #
    # Direct I/O connections
    #
    connectors = [
        Connector("pmod", 0, "4 2 47 45 44 48 46 44")
    ]


    @classmethod
    def _get_badge_connection(cls):
        """ Returns a serial connection to our MCH badge. """

        candidates = []

        # Search all of our ports for an MCH badge.
        for port in serial.tools.list_ports.comports():

            # Skip ports with no USB data available.
            if not hasattr(port, 'pid'):
                continue

            # If we've found an MCH badge, return it.
            if (port.vid, port.pid) == (cls.VENDOR_ID, cls.PRODUCT_ID):
                candidates.append(port.device)

        # If we've found one or more candidates; grab the first one.
        if candidates:
            candidates.sort()
            return serial.Serial(candidates[0], 115200, timeout=1.0)
        else:
            return None


    def toolchain_program(self, products, name):

        # This number is mostly meaningless; it just divides nicely
        # into our encoded size, while looking incredibly unholy.
        CHUNK_SIZE = 157 * 13 * 17

        # Find ourselves the badge we want to program.
        badge = self._get_badge_connection()
        if badge is None:
            raise IOError("could not find a badge to program!")

        # Get the bitstream itself, encoded base64 for transfer.
        bitstream = products.get("{}.bin".format(name))
        bitstream = bytearray(binascii.b2a_base64(bitstream).strip())

        # Create a quick helper we can use to execute python code in the raw REPL.
        # This executes a command, and then issues CTRL+D to accept it.
        def _exec(command):
            badge.write(command)
            badge.write(b"\x04")

        # Press CTRL+C on the badge to get to our micropython prompt.
        badge.write(b"\r\x03")
        time.sleep(3.5)
        badge.write(b"\r\x03")

        # And wait until the device is ready.
        badge.read_until("\r>>")

        # Press CTRL+A on the badge to get to our RAW repl.
        badge.write(b"\r\x01")
        badge.read_until("CTRL-B")

        # Set up our communications...
        _exec(b"import ice40")
        _exec(b"import binascii")

        # ... transfer over our encoded bitstream...
        _exec(b"b = b''")

        print(len(bitstream))

        while bitstream:

            # Extract the chunk to copy over...
            chunk = bitstream[0:CHUNK_SIZE]
            del bitstream[0:CHUNK_SIZE]

            # ... and do the actual data copy.
            encoded_literal = repr(bytes(chunk)).encode('ascii')
            _exec(b'b += "' + chunk + b'"')

        # Convert the bitstream back into its original binary format.
        _exec(b"print(len(b))")
        _exec(b"b = binascii.a2b_base64(b)")

        ## Finally, load the bitstream onto the ice40.
        _exec(b"print(len(b))")
        _exec(b"ice40.load(bytes(b))")

        ## ... and clear it from memory.
        _exec(b"del b")

        # Press CTRL+B to complete the REPL interaction.
        badge.write(b"\r\x02")

        # XXX debug
        time.sleep(1)
        print(badge.read(65536 * 10).decode('ascii'))



if __name__ == "__main__":
    from nmigen_boards.test.blinky import Blinky
    MCH2021BadgePrototype1().build(Blinky(), do_program=True)
