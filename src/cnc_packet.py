#!/usr/bin/python2
import struct
import tempfile
import subprocess
import os
from itertools import izip_longest

from image import DellImage, get_control_struct

def command(cmd, msg):
    try:
        subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
    except subprocess.CalledProcessError as e:
        print("#" * 80)
        print(e.output)
        print("#" * 80)
        raise Exception(msg)

# whyyy isn't this built-in
def group(n, iterable, fillvalue=None):
    """
    groups an iterable into chunks of n, filling the last chunk with fillvalue
    if there's anything left over.
    """
    args = [iter(iterable)] * n
    return izip_longest(fillvalue=fillvalue, *args)

# builds a packet that can be placed in an image
def build_image_packet(data):
    magic = '\xac\x6b'
    trailer = '\xb6\xca'
    length = len(data) + len(trailer)
    len_str = struct.pack('<H', length)
    # the 0 after the length is padding to make the decoding logic easier
    return magic + len_str + '\x00' + data + trailer

def build_write_packet(address, data):
    address_str = chr(address & 0xFF) + \
                  chr((address >> 8) & 0xFF) + \
                  chr((address >> 16) & 0xFF)
    return build_image_packet('\x00' + address_str + data)

def build_execute_packet(address, code):
    address_str = chr(address & 0xFF) + \
                  chr((address >> 8) & 0xFF) + \
                  chr((address >> 16) & 0xFF)
    return build_image_packet('\x02' + address_str + code)

def build_clut_blob(table, offset, size):
    table = table[:size]
    return struct.pack('<H', offset) + struct.pack('<H', size) + table

def build_sdram_blob(data, img_width, img_height, clut_offset, sdram_offset):
    width = int(img_width)
    height = img_height
    size = len(data)
    data = "".join(chr(ord(c) + clut_offset) for c in data)

    return struct.pack('<H', size) + \
            struct.pack('<H', sdram_offset) + \
            struct.pack('<H', height) + \
            struct.pack('<H', width) + data

def build_command_blob(x, y, img_width, img_height, sdram_offset, tile):
    control = get_control_struct(img_width, img_height, x, y, sdram_offset)
    tiles = [0x78, 0x1e0, 0x230, 0x050]
    offset = tiles[tile]
    return struct.pack('<H', offset) + control

def build_image_blob(image, x, y, clut_offset=0, sdram_offset=0, tile=0):
    return build_clut_blob(image.table, clut_offset * 4, image.colors * 4) + \
            build_sdram_blob(image.image, image.width, image.height,
                             clut_offset, sdram_offset << 6) + \
            build_command_blob(x, y, image.width, image.height, sdram_offset,
                               tile)

def build_upload_packet(blob):
    return build_image_packet('\x03' + blob)

def build_cursor_packet(x_pos, y_pos):
    return build_image_packet('\x04' + \
                              struct.pack('<H', x_pos) + \
                              struct.pack('<H', y_pos))

def build_gif(packet, output_file):
    image_names = []
    blue = 0
    for bytes in group(8, map(ord, packet), fillvalue=255):
        f, name = tempfile.mkstemp(suffix=".ppm")
        image_names.append(name)
        os.write(f, "P3\n")
        os.write(f, "3 1\n")
        os.write(f, "255\n")
        os.write(f, "%d %d %d  " % (bytes[0], bytes[1], blue))
        os.write(f, "%d %d %d  " % (bytes[2], bytes[3], bytes[4]))
        os.write(f, "%d %d %d  " % (bytes[5], bytes[6], bytes[7]))
        blue = 1 - blue
        os.close(f)
    command("convert -delay 10 -loop 1 " + " ".join(image_names) + " " + output_file, "gif creation failed!")

def build_upload_gif(x_pos, y_pos, input_file, output_file,
                     clut_offset=0, sdram_offset=0, tile=0):
    image = DellImage(input_file, 255 - clut_offset)
    packet = build_upload_packet(build_image_blob(image, x_pos, y_pos,
                                                  clut_offset, sdram_offset, tile))
    build_gif(packet, output_file)

if __name__ == "__main__":
    packet = build_write_packet(0xc1e0 + 0x26, '\x14')
    build_gif(packet, "write.gif")
    build_upload_gif(100, 100, "lock_https.gif", "lock.gif", clut_offset=17, sdram_offset=0x1000>>6, tile=1)

