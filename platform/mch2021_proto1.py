#
# MCH2021 Badge Platform
#

import os
import subprocess

from nmigen.build import *
from nmigen.vendor.lattice_ice40 import LatticeICE40Platform

from nmigen_boards.resources import *


class MCH2021BadgePrototype1(LatticeICE40Platform):
    """ Platform for 'Prototype 1' MCH2021 Badges. """

    device  = "iCE40UP5K"
    package = "SG48"

    # For now, use the iCE40's internal oscillator as our default, as it's
    # there no matter what firmware's running on the ESP32.
    default_clk = "SB_HFOSC"

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


    #
    # TODO: implement toolchain_program, once we have a simple interface via the STM32
    #


if __name__ == "__main__":
    from nmigen_boards.test.blinky import Blinky
    MCH2021BadgePrototype1().build(Blinky(), do_program=True)
