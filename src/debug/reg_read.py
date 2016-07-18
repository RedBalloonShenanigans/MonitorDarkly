#!/usr/bin/python2
import protocol
import delltools
import sys

reg_num = int(sys.argv[1], 16)
assert reg_num <= 0xffff

dell = protocol.Dell2410()
dell.initialize()
dell.debug_on()
bytes = dell.reg_read(reg_num)
value = ord(bytes[0]) | (ord(bytes[1]) << 8)
print "The value at %s is: %s" % (hex(reg_num), hex(value))
dell.debug_off()

