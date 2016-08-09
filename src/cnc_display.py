#!/usr/bin/python2

import pygame as pg
import tempfile
import os
import sys
import time
import struct
from itertools import izip_longest

import cnc_packet
import image

def group(n, iterable, fillvalue=None):
    """
    groups an iterable into chunks of n, filling the last chunk with fillvalue
    if there's anything left over.
    """
    args = [iter(iterable)] * n
    return izip_longest(fillvalue=fillvalue, *args)

def display_frame():
    for event in pg.event.get():
        if event.type == pg.QUIT:
            sys.exit(0)

        if event.type == pg.KEYDOWN:
            if event.key == pg.K_q:
                sys.exit(0)


    pg.display.flip()

def display_packet(packet, screen):
    screen.fill((255, 255, 255))

    # display the pixel for as many frames it takes to read it
    start = pg.time.get_ticks()
    blue = 0
    for bytes in group(8, map(ord, packet), fillvalue=255):
        screen.set_at((675, 641), (bytes[0], bytes[1], blue))
        screen.set_at((676, 641), (bytes[2], bytes[3], bytes[4]))
        screen.set_at((677, 641), (bytes[5], bytes[6], bytes[7]))
        for _ in xrange(3):
            display_frame()
        pg.time.delay(20 * 3)
        blue = 1 - blue
    end = pg.time.get_ticks()

def main():
    pg.init()
    screen = pg.display.set_mode((1920,1200), pg.FULLSCREEN|pg.DOUBLEBUF|pg.HWSURFACE)

    lock = image.DellImage("lock_https.gif")
    packet = cnc_packet.build_upload_packet(cnc_packet.build_image_blob(lock, 50, 50))
    display_packet(packet, screen)

    while True:
        x, y = pg.mouse.get_pos()
        packet = cnc_packet.build_cursor_packet(x, y)
        display_packet(packet, screen)


if __name__ == "__main__":
    main()
