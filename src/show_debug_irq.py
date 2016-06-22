#!/usr/bin/python2
import protocol
import delltools
import binascii
from payload import X86Payload

payload = X86Payload("show_debug_irq")
dell = protocol.Dell2410()
dell.initialize()
dell.debug_on()
delltools.execute_payload(dell, payload, 0x500)
bytes = dell.reg_read(0x3a5a)
value = ord(bytes[0]) | (ord(bytes[1]) << 8)
print "The value at 0x3a5a is: %s" % hex(value)
dell.debug_off()
