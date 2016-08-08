#!/usr/bin/python2
import protocol
import delltools
import sys

try:
    vertical_coord = int(sys.argv[1])
    horizontal_coord = int(sys.argv[2])
except ValueError:
    print 'Coordinates should be provided in decimal'

ACTIVE_WINDOW_Y_OFFSET = 0x1f
ACTIVE_WINDOW_X_OFFSET = 0x5d


dell = protocol.Dell2410()
dell.initialize()
dell.debug_on()
print delltools.grab_pixel(dell, ACTIVE_WINDOW_Y_OFFSET + vertical_coord,
                           ACTIVE_WINDOW_X_OFFSET + horizontal_coord)
dell.debug_off()
