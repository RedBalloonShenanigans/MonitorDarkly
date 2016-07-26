import struct
import copy
import time

from payload import X86Payload
from protocol import Dell2410
from image import get_control_struct

VERBOSE = False


FREE_REG_ADDR_START = 0x3a5a
FREE_REG_ADDR_END = 0x3a60

SRAM_CMD_MEM_START = 0xc000
SRAM_CMD_MEM_END = 0xc800
SEGMENT_MAX_LIMIT = 2 ** 16


def mem_write(dev, addr, data):
    cur = addr
    while cur < addr + len(data):
        next_ = min(cur + 110, addr + len(data))
        # see comment in mem_read()
        if next_ & 0xffff0000 != cur & 0xffff0000:
            next_ = next_ & 0xffff0000
        dev.ram_write_2(cur, data[cur - addr:next_ - addr])
        cur = next_


def mem_read(dev, start, l=0x2000):
    cur = start
    mem = ''
    while cur < start + l:
        next_ = min(cur + 120, start + l)
        # the segment + offset in ram_read_2 is computed as:
        # segment = (address & 0xffff0000) >> 8
        # offset = address & 0xffff
        # and if we go far enough that address_lo wraps around, then we'll
        # wrap around and get stuff from the beginning of the segment
        if next_ & 0xffff0000 != cur & 0xffff0000:
            next_ = next_ & 0xffff0000
        mem += dev.ram_read_2(cur, next_ - cur)
        cur = next_
    return mem


def execute_payload(dev, payload, ram_addr=0x6000):
    mem_write(dev, ram_addr, payload.data)
    dev.execute_2(ram_addr)


def clear_0xc000(dev):
    for i in range(SRAM_CMD_MEM_START, SRAM_CMD_MEM_END, 100):
        dev.ram_write(i, '\x00' * 100)


def upload_single_image(dev, image, upload_address):
    addr = upload_address
    width = image.width
    stride = image.width
    height = image.height
    mem_write(dev, addr, image.image)
    addr += len(image.image)
    print "uploaded image at %s, size %s" % (hex(upload_address), hex(len(image.image)))
    return (width, height, stride, upload_address, image.table), addr


def all_images_upload(dev, images, start_address=0x600000):
    clear_0xc000(dev)
    meta_infos = []
    offset = start_address
    for image in images:
        meta_info, offset = upload_single_image(dev, image, offset)
        meta_infos.append(meta_info)
    return meta_infos


def put_image(dev, images_metainfo, x=0, y=0):
    clut_table = images_metainfo[4]
    width = images_metainfo[0]
    height = images_metainfo[1]
    stride = images_metainfo[2]
    upload_address = images_metainfo[3]
    clear_0xc000(dev)
    sdram_write(dev, src=upload_address,
                dest=0, height=height, width=width,
                dest_stride=stride)

    transfer_clut(dev, clut_table)
    control = get_control_struct(width, height, x, y)
    mem_write(dev, 0xc078, control)

def sdram_read(dev, src, dest, height, width, src_stride):
    # The IROM sdram_read function has a similar bug to sdram_write, where the
    # offset can't be >64k, so we need a similar fix.
    assert width < 0x10000
    while height > 0:
        sdram_lo = src & 0xffff
        sdram_hi = src >> 16
        dest_off = dest & 0xff
        dest_seg = dest >> 8
        new_height = height
        while dest_off + new_height * width > 0x10000:
            new_height -= 1
        _sdram_read(dev, dest_seg, dest_off, 0, sdram_hi, sdram_lo, new_height,
                    width, src_stride)
        src += width * new_height
        dest += width * new_height
        height -= new_height



def _sdram_read(dev, dst_seg, dst_off=0, read_off=0, sdram_hi=0, sdram_lo=0, height=0,
                width=0, stride=0, ram_write_addr=0x500):
    payload = X86Payload("sdram_read")
    payload.replace_word(0xadad, dst_off)
    payload.replace_word(0xa1a1, dst_seg)
    payload.replace_word(0xacac, read_off)
    payload.replace_word(0xaeae, height)
    payload.replace_word(0xafaf, width)
    payload.replace_word(0xbdbd, stride)
    payload.replace_word(0xbcbc, sdram_hi)
    payload.replace_word(0xbebe, sdram_lo)
    execute_payload(dev, payload, ram_write_addr)


def sdram_write(dev, src, dest, height, width, dest_stride):
    # The IROM sdram_write function has a bug where if the source offset goes
    # beyond 64k, rather than incrementing the segment register, it wraps
    # around and starts reading from the beginning of the segment. To fix this,
    # we need to split up the write. Complicating the matter is the fact that
    # we can't start a transfer in the middle of a row, so we can only transfer
    # whole rows at a time. This code deals with both constraints in order to
    # correctly upload images >64k in size.
    assert width < 0x10000
    while height > 0:
        reg_lo = dest & 0xffff
        reg_hi = dest >> 16
        src_off = src & 0xff
        src_seg = src >> 8
        new_height = height
        while src_off + new_height * width > 0x10000:
            new_height -= 1
        _sdram_write(dev, src_seg, src_off, reg_hi, reg_lo, new_height, width,
                    dest_stride)
        src += width * new_height
        dest += width * new_height
        height -= new_height


def _sdram_write(dev, src_seg=0, src_off=0, reg_hi=0, reg_lo=0, height=0, width=0,
                 stride=0, ram_write_addr=0x600):
    payload = X86Payload("sdram_write")
    payload.replace_word(0xacac, src_off)
    payload.replace_word(0xadad, src_seg)
    payload.replace_word(0xaeae, height)
    payload.replace_word(0xafaf, width)
    payload.replace_word(0xbdbd, stride)
    payload.replace_word(0xbcbc, reg_hi)
    payload.replace_word(0xbebe, reg_lo)
    execute_payload(dev, payload, ram_write_addr)


def memcpy(dev, dst_seg, src_seg, dst_off, src_off, len):
    payload = X86Payload("memcpy")
    payload.replace_word(0xadad, dst_seg)
    payload.replace_word(0xabab, src_seg)
    payload.replace_word(0xacac, dst_off)
    payload.replace_word(0xaeae, src_off)
    payload.replace_word(0xafaf, len)
    execute_payload(dev, payload, 0x600)


def grab_pixel(dev, vertical_coord, horizontal_coord, memory_dump_addr=0x4000):
    """grab pixel values in R G B format """
    payload = X86Payload("grab_pixel")
    payload.replace_word(0xaeae, vertical_coord)
    payload.replace_word(0xbebe, horizontal_coord)
    payload.replace_word(0xcece, memory_dump_addr)
    execute_payload(dev, payload, 0x600)
    extracted_dump_data = mem_read(dev, memory_dump_addr, l=0x6)

    color_val = {
        'R': struct.unpack('<H', extracted_dump_data[:2]),
        'G': struct.unpack('<H', extracted_dump_data[2:4]),
        'B': struct.unpack('<H', extracted_dump_data[4:6]),
    }
    return color_val


def grab_pixel_imp(dev, vertical_coord, horizontal_coord, memory_dump_addr=0x4000):
    """grab pixel values using the Input Main Processor"""
    payload = X86Payload("grab_pixel_imp")
    payload.replace_word(0xadad, vertical_coord)
    payload.replace_word(0xacac, horizontal_coord)
    payload.replace_word(0xaeae, memory_dump_addr)
    execute_payload(dev, payload, 0x600)
    extracted_dump_data = mem_read(dev, memory_dump_addr, l=0x6)

    color_val = {
        'R': struct.unpack('<H', extracted_dump_data[:2])[0],
        'G': struct.unpack('<H', extracted_dump_data[2:4])[0],
        'B': struct.unpack('<H', extracted_dump_data[4:6])[0],
    }
    return color_val


def transfer_clut(dev, clut_table, clut_low=0x7000):
    payload = X86Payload("transfer_clut")
    payload.replace_word(0xadad, 0x0000)  # clut_high
    payload.replace_word(0xacac, clut_low)
    mem_write(dev, clut_low, clut_table)
    execute_payload(dev, payload, 0x600)
