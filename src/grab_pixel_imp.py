#!/usr/bin/python2
import time
import sys

import protocol
import delltools
from payload import X86Payload

x_coord = int(sys.argv[1])
y_coord = int(sys.argv[2])

dell = protocol.Dell2410()
dell.initialize()
dell.debug_on()
color = delltools.grab_pixel_imp(dell, y_coord, x_coord)
print "R: %d, G: %d, B: %d" % (color['R'], color['G'], color['B'])
dell.debug_off()
