#!/usr/bin/python2
import protocol
import delltools
import sys
from itertools import izip
import binascii

def group(iterable, n):
    args = [iter(iterable)] * n
    return izip(*args)

def print_memory(data):
    for chunk in group(data, 16):
        print ''.join(binascii.hexlify(byte) + " " for byte in chunk)
    print ''

start = int(sys.argv[1], 16)
len = int(sys.argv[2], 16)

dell = protocol.Dell2410()
dell.initialize()
dell.debug_on()
data = delltools.mem_read(dell, start, len)
dell.debug_off()

print_memory(data)
