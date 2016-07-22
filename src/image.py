import os
import tempfile
import subprocess
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
    # max size supported right now.
    max_image_size = 256000
    max_colors = 256

    def __init__(self, filename, raw_data=None):
        self.filename = os.path.join(IMAGE_PATH, filename)
        self.width, self.height = self._get_image_dimensions(self.filename,
                                                             self.max_image_size)
        self.raw_data = raw_data or self._convert()
        self.image, self.table = self._generate()

    @staticmethod
    def _get_image_dimensions(filename, max_image_size):
        with Image(filename=filename) as img:
            print(img.size)
            width = img.size[0]
            height = img.size[1]
            if width % 2 != 0:
                width -= 1
            if height % 2 != 0:
                height -= 1

            # this is broken as right now either control structure or
            # sdram_write is not properly configured.
            # For the time being we can only display 2**16 bytes.
            if width <= 0 or height <= 0 or \
                    (width * height) > max_image_size:
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
        # encode the clut the way monitor reads
        for i in range(self.max_colors):
            index = i * 3
            table += palette[index] + chr(0) + palette[index + 2] + palette[index + 1]
        return self.raw_data, table
