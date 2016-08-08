#!/usr/bin/python2
import protocol
import delltools
import time
from payload import X86Payload

payload = X86Payload("cnc")
dell = protocol.Dell2410()
dell.initialize()
dell.debug_on()

delltools.execute_payload(dell, payload, 0x6000)
time.sleep(2)

dell.debug_off()

