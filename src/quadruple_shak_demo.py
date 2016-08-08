#!/usr/bin/python2
import protocol
import delltools
from image import DellImage, get_control_struct
import struct


def put_lock_8(dev, images_metainfo, x, y):
    clut_table = images_metainfo[4]
    width = images_metainfo[0]
    height = images_metainfo[1]
    stride = images_metainfo[2]
    upload_address = images_metainfo[3]
    control_pak_addrs = [0xc078, 0xc1e0, 0xc230, 0xc050]
    for addr in control_pak_addrs:
        dev.reg_write(addr + 0x26, 0)
    delltools.sdram_write(dev, src=upload_address,
                          dest=0, height=height, width=width,
                          dest_stride=stride)

    for addr in control_pak_addrs:
        delltools.transfer_clut(dev, clut_table)
        control = get_control_struct(width, height, x, y)
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
