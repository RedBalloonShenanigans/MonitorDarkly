#!/usr/bin/python2

from select import poll, POLLERR, POLLPRI
from os import system, path
from time import sleep, time
import sys
import protocol
import demo

ATTACK = 0

flag = False

GPIO_BASE = 151

# sysfs GPIO paths
GPIO_PREFIX = "/sys/class/gpio/"
GPIO_EXP = GPIO_PREFIX + "export"
GPIO_UXP = GPIO_PREFIX + "unexport"

# LED path in sysfs
LED_PREFIX = "/sys/devices/platform/leds/leds/LED/"
LED_TRIGGER = "trigger"
LED_BRIGHT = "brightness"

GPIO = {}
for i in range(1, 8):
    GPIO[i] = GPIO_PREFIX + "gpio" + str(GPIO_BASE + i) + "/"

# GPIO files in sysfs
GPIO_VAL = "value"
GPIO_EDG = "edge"
GPIO_DIR = "direction"

# GPIO direction settings in sysfs
DIR_IN = "in"
DIR_OUT = "out"
# GPIO edge settings in sysfs
EDGE_RISE = "rising"
EDGE_FALL = "falling"
EDGE_NONE = "none"


def grab_led():
    with open(LED_PREFIX + LED_TRIGGER, "w") as fp:
        fp.write("none")


def blink_led(count, delay, launch):
    for i in range(count << 1):
        with open(LED_PREFIX + LED_BRIGHT, "w") as fp:
            fp.write(str((i + 1) % 2))
            sleep(delay)
    if launch and ATTACK > 0:
        attack_funcs = [demo.put_unicorn,
                        demo.put_ssl_lock,
                        demo.put_shak,
                        demo.red_hmi,
                        demo.no_image]
        if ATTACK < 6:
            attack_funcs[ATTACK - 1](dell, image_infos)


def setup_gpio(number, direction, edge=EDGE_NONE, verbose=False):
    try:
        if verbose:
            print("Setting GPIO {}".format(number))
        if not path.exists(GPIO[number]):
            with open(GPIO_EXP, "w") as fp:
                fp.write(str(GPIO_BASE + number))
        with open(GPIO[number] + GPIO_DIR, "w") as fp:
            fp.write(direction)
        with open(GPIO[number] + GPIO_EDG, "w") as fp:
            fp.write(edge)
    except:
        raise


def handle_button(fp, last, count, function, *args):
    fp.seek(0)
    level = int(fp.read()[0])
    delay = time() - last
    last = time()
    if delay < 0.01:
        return last, count
    count += 1
    # New code
    function(*args)
    return last, count
    # Old code
    if count % 2 == 0:
        if level == 1:
            function(*args)
        else:
            count -= 1
    return last, count

dell = protocol.Dell2410()
dell.initialize()
dell.debug_on()
image_infos = demo.upload_demo_images(dell)

grab_led()
# Launch button
setup_gpio(3, DIR_IN, EDGE_RISE, True)
# Switch button
setup_gpio(7, DIR_IN, EDGE_RISE, True)

fp = [0, 0]
fp[0] = open(GPIO[3] + GPIO_VAL, "r")
fp[1] = open(GPIO[7] + GPIO_VAL, "r")

p = poll()
p.register(fp[0].fileno(), POLLPRI | POLLERR)
p.register(fp[1].fileno(), POLLPRI | POLLERR)

# Flush garbage...
events = p.poll(0)
if len(events) > 0:
    fp[0].read()
    fp[1].read()

count = [0, 0]
last = [time(), time()]
while True:
    events = p.poll(2000)
    while len(events) > 0:
        e = events.pop()
        for i in range(2):
            if e[0] == fp[i].fileno():
                n = i
                break
        if i == 0:
            number = ((count[n]) % 6) + 1
            delay = 0.1
            ATTACK = number
            launch = False
        else:
            number = 10
            delay = 0.02
            launch = True
        print "pass"
        last[n], count[n] = handle_button(
            fp[n], last[n], count[n], blink_led, number, delay, launch)
        if launch:
            count = [0, 0]
