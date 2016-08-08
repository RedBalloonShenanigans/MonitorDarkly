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

def display_frame():
    for event in pg.event.get():
        if event.type == pg.QUIT:
            sys.exit(0)

        if event.type == pg.KEYDOWN:
            if event.key == pg.K_q:
                sys.exit(0)


    pg.display.flip()

def display_packet(packet, screen):
    # the number of pixels that need to be processed
    num_pixels = (len(packet) + 2) // 3
    screen.fill((255, 255, 255))

    # display the pixel for as many frames it takes to read it
    start = pg.time.get_ticks()
    blue = 0
    for red, green in izip_longest(map(ord, packet[0::2]),
                                   map(ord, packet[1::2]),
                                   fillvalue=0):
        screen.set_at((397, 642), (red, green, blue))
        display_frame()
        pg.time.delay(17)
        blue = 1 - blue
    end = pg.time.get_ticks()

def main():
    pg.init()
    screen = pg.display.set_mode((1920,1200), pg.FULLSCREEN|pg.DOUBLEBUF|pg.HWSURFACE)

    lock = image.DellImage("https_lock.gif")
    packet = cnc_packet.build_upload_packet(cnc_packet.build_image_blob(lock, 50, 50))
    display_packet(packet, screen)

    while True:
        x, y = pg.mouse.get_pos()
        packet = cnc_packet.build_cursor_packet(x, y)
        display_packet(packet, screen)


if __name__ == "__main__":
    main()
