import os
import struct

THIS_PATH = os.path.dirname(os.path.realpath(__file__))
PAYLOAD_PATH = os.path.join(THIS_PATH, "../payloads")

class X86Payload:

    def __init__(self, filename):
        filename = os.path.join(PAYLOAD_PATH, filename)
        with open(filename, "r") as f:
            magic = f.read(8)
            # all our payloads use pusha
            # i dont like it but whatever...
            assert magic == "\x01\x03\x10\x10\x20\x00\x00\x00"
            header = f.read(24)
            length = struct.unpack("<H", header[0:2])[0]
            self.data = f.read(length)

    def replace_word(self, orig, new):
        self.data = self.data.replace(struct.pack('<H', orig), struct.pack('<H', new))
        pass
