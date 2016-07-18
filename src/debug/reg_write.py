#!/usr/bin/python2
import protocol
import delltools
import sys

reg_num = int(sys.argv[1], 16)
assert reg_num <= 0xffff
reg_value = int(sys.argv[2], 16)
assert reg_value <= 0xffff

dell = protocol.Dell2410()
dell.initialize()
dell.debug_on()
bytes = dell.reg_write(reg_num, reg_value)
dell.debug_off()

