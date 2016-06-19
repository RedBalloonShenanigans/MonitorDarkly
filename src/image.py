import os
import tempfile
import subprocess
try:
    from wand.image import Image
except:
    print("Install the wand package using pip if you want image support")

THIS_PATH = os.path.dirname(os.path.realpath(__file__))
IMAGE_PATH = os.path.join(THIS_PATH, "../images")


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

    def __init__(self, filename, width=None, height=None, transparency=None):
        self.filename = os.path.join(IMAGE_PATH, filename)
        self.width = width
        self.height = height
        self.transparency = transparency
        self.raw_data = self._convert()
        self.image, self.table = self._generate()

    def _convert(self):
        with Image(filename=self.filename) as img:
            print(img.size)
            if self.width is None or self.width > img.size[0]:
                self.width = img.size[0]
            if self.height is None or self.height > img.size[1]:
                self.height = img.size[1]
            if self.width % 2 != 0:
                self.width -= 1
            if self.height % 2 != 0:
                self.height -= 1
            # Minumum and maximum
            # Maximum size is based on experimentation, real value is unknown at this time
            if self.width <= 0 or self.height <= 0 or \
                    (self.width * self.height) > self.max_image_size:
                raise Exception("Invalid image size {0} x {1}".format(self.width, self.height))
            # Figure out how to use this properly?!?!
        # Backup solution
        fd, fileout = tempfile.mkstemp(suffix=".pcx")
        os.close(fd)
        # 15 colors, not 16, because index 0 is reserved for transparency
        cmd = "convert -colors {0} -depth {1} -compress none {2} {3}".format(
            15, 8, self.filename, fileout)
        command(cmd, "Image failed!")
        with open(fileout, "r") as f:
            # Header...garbage!
            f.read(128)
            raw_data = f.read()
        os.remove(fileout)
        return raw_data

    def _generate(self):
        image = ""
        for i in range(int(self.height * self.width / 2)):
            j = i * 2
            data = bytearray(self.raw_data[j:j + 2])
            if self.transparency is None:
                b = (data[1] << 4) | data[0]
                # Index 0 is always transparency so we adjust
                b += 0x11
            else:
                b = 0
                if data[1] != self.transparency:
                    b = data[1] << 4
                    b += 0x10
                if data[0] != self.transparency:
                    b |= data[0]
                    b += 1
            image += chr(b)
        # 0 padding, not sure why yet, but this can cause issues
        image += "\x00" * 100
        palette = self.raw_data[-768:-768 + (16 * 3)]
        table = ""
        for i in range(16):
            index = i * 3
            table += palette[index] + chr(0) + palette[index + 2] + palette[index + 1]
        return image, table
