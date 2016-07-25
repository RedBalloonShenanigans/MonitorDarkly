#!/usr/bin/python2
import protocol
import delltools
from image import DellImage
import struct


def put_lock_8(dev, images_metainfo, x, y):
    clut_table = images_metainfo[4]
    width = images_metainfo[0]
    height = images_metainfo[1]
    stride = images_metainfo[2]
    upload_address = images_metainfo[3]
    delltools.clear_0xc000(dev)
    delltools.sdram_write(dev, src=upload_address,
                          dest=0, height=height, width=width,
                          dest_stride=stride)
    control_pak_addrs = [0xc078, 0xc1e0, 0xc230, 0xc050]

    for addr in control_pak_addrs:
        delltools.transfer_clut(dev, clut_table)
        control = '\x00' * 24                   # [:24]
        control += '\xff\xff'                   # color
        control += struct.pack('<H', x)         # x coord
        control += struct.pack('<H', int(width) / 2)     # width
        control += struct.pack('<H', int(width) / 2)     # expansion level!?
        control += '\x00\x00'                   # sdram location
        control += struct.pack('<H', height)    # height
        control += struct.pack('<H', y)         # y coord
        control += '\x14\x00'                   # transperency and patterns , 8 bits only
        delltools.mem_write(dev, addr, control)
        x = x * 3
        y = y * 2 + 10

if __name__ == "__main__":
    dell = protocol.Dell2410()
    dell.initialize()
    dell.debug_on()
    lock_image = DellImage('shak_crop.gif')
    upload_address = 0x400000
    metainfo, off = delltools.upload_single_image(dell, lock_image, upload_address)
    put_lock_8(dell, metainfo, 0x30, 0x39)
    dell.debug_off()
