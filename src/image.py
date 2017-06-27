"""
This module deals with generating image data in a way that can be displayed by
the monitor. When the monitor's OSD displays something, there are three parts
that are involved:

1. Tile data
2. Image data
3. Color Look Up Table (CLUT)

The OSD calls each image being displayed a "tile". There can be up to 16 tiles
displayed at a time, but the actual maximum is based on a register programmed
by the firmware on startup. Furthermore, there are two sets of tiles. One set
is displayed, and the other set isn't. This allows only updating the
not-displayed set, and then switching sets by flipping a bit in a register. We
ignore this, though, and always use the currently active set of tiles.

The tiles themselves exist in a special SRAM command memory (mapped to 0xc000),
and each one is represented by a 40-byte control structure. This control
structure specifies metadata like the width and height of an image, its bpp
(bits per pixel), as well as where the other two parts of the image (image data
and clut) are located. See get_control_struct() for details on the format.

The image data and color look up table together make up the actual content of
the image. Each pixel of the image consists of a number of bits (the precise
number is the bpp, which is specified in the tile data) which is interpreted as
an index into an appropriately-sized color look up table. The CLUT gives the
full 24-bit color (8 bits per channel) for each index. Each CLUT entry is 4
bytes, although 1 byte is unused. 1bpp through 8bpp are claimed to be
supported, although we've only tried 4bpp and 8bpp. Our current implementation
hard-codes 8bpp.

The image data is put in a special piece of memory that can be accessed using
the sdram_read/sdram_write API's exposed by the IROM. These functions support
fully general strided transfers with an offset, so you can blit to an arbitrary
rectangle inside the image. They also support some weirdo data expansion thing,
though I don't know how it's useful with the CLUT already there. The CLUT is
written to using another, more general, IROM API which transfers all sorts of
tables used by the fixed-function hardware. There is a helper for just
transferring the CLUT, though.

The area of memory reserved for the CLUT is 2048 bytes. In 4bpp mode, each tile
can select between 16 different CLUTs using 4 bits in the control structure.
The CLUT's are all right next to each other, so CLUT 0 starts at 0, CLUT 1
starts at 16 * 4, etc. In 8bpp mode, there is only one CLUT starting at 0. It's
possible for multiple tiles to "share" the CLUT, though, if the second one
offsets all its indices. This is how we handle multiple images.

In 4bpp mode, index 0 is reserved to mean a fully-transparent pixel (alpha =
0), and the CLUT entry for 0 is ignored. In 8bpp, index 255 is reserved
instead. Beyond that, there is supposedly some support for partially
transparent pixels through some "BLEND" registers which let you specifiy the
alpha for certain subsets of indices, but I haven't figured out how to get that
working. Also, the BLEND registers affect all the tiles that have blending
enabled the same, so it would be difficult to convert traditional images using
RGBA to the scheme if you want to display multiple images.

Things that aren't fully understood:

- Hilight windows. We know where the enable bits are (there are two sets, one in
registers and another in the tile control structures), and we know that the
first 24 bytes of the tile control structure consists of 6 bytes of data for
each hilight window, but we don't know the format of that data.
- The previously-mentioned blending feature. Theoretically we just need to find
the enable bit.
- The blink enable bit in the control struct. <blink>, anyone?
- Why is there twice as much storage available for CLUT's compared to how much
is actually used?
"""

import os
import tempfile
import subprocess
import struct
try:
    from wand.image import Image
except:
    print("Install the wand package using pip if you want image support")

THIS_PATH = os.path.dirname(os.path.realpath(__file__))
IMAGE_PATH = os.path.join(THIS_PATH, "../images")
PCX_CLUT_OFFSET = -768
PCX_HEADER_LEN = 128


def command(cmd, msg):
    try:
        subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
    except subprocess.CalledProcessError as e:
        print("#" * 80)
        print(e.output)
        print("#" * 80)
        raise Exception(msg)


class DellImage:
    def __init__(self, filename, max_colors=255):
        self.filename = os.path.join(IMAGE_PATH, filename)
        self.max_colors = max_colors
        self.width, self.height = self._get_image_dimensions(self.filename)
        self.raw_data = self._convert()
        self.image, self.table = self._generate()

    @staticmethod
    def _get_image_dimensions(filename):
        with Image(filename=filename) as img:
            print(img.size)
            width = img.size[0]
            height = img.size[1]
            if width % 2 != 0:
                width -= 1
            if height % 2 != 0:
                height -= 1

            if width <= 0 or height <= 0:
                raise Exception("Invalid image size {0} x {1}".format(width, height))
        return width, height

    def _convert(self):
        fd, fileout = tempfile.mkstemp(suffix=".pcx")
        os.close(fd)
        cmd = "convert -colors {0} -depth {1} -compress none {2} {3}".format(
            self.max_colors, 8, self.filename, fileout)
        command(cmd, "Image failed!")
        with open(fileout, "r") as f:
            raw_data = f.read()[PCX_HEADER_LEN:]
        os.remove(fileout)
        return raw_data

    def _generate(self):
        palette = self.raw_data[PCX_CLUT_OFFSET:]
        table = ""
        image = self.raw_data[:self.width*self.height]
        self.colors = max(map(ord, image)) + 1
        # encode the clut the way monitor reads
        for i in range(self.colors):
            index = i * 3
            table += palette[index] + chr(0) + palette[index + 2] + palette[index + 1]
        return image, table

def get_control_struct(width, height, x=0, y=0, sdram_loc=0):
    # note: sdram location is in units of 2^6 bytes
    control = '\x00' * 24                           # hilight window info
    control += '\x04'                               # unknown
    # bits 4-7 are hilight window enable bits
    # for 4bpp, the bits 0-3 control which LUT gets used
    # 0 -> offset = 0
    # 1 -> offset = 1 * 16 * 4
    # 2 -> offset = 2 * 16 * 4
    # etc.
    control += '\x00'
    control += struct.pack('<H', x / 2)             # x coord
    control += struct.pack('<H', int(width) / 2)    # width
    control += struct.pack('<H', int(width) / 2)    # stride
    control += struct.pack('<H', sdram_loc & 0xffff) # sdram location (low 8 bits)
    control += struct.pack('<H', height)            # height
    control += struct.pack('<H', y)                 # y coord
    # lower 3 bits set up the bit per pixel mode for the monitor
    # 000 : disabled
    # 011 : 4 bpp
    # 100 : 8 bpp
    # the rest of the bits are unknown flags
    control += '\x14'
    control += chr(sdram_loc >> 16)                 # sdram location (high 4 bits)
    return control
