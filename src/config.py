import ConfigParser
import os

"""Pulls config info from a config.ini file at the top level. This includes
whether to be verbose, what method to use to send DDC2bi commands, etc.
"""

THIS_PATH = os.path.dirname(os.path.realpath(__file__))
CONFIG_PATH = os.path.join(THIS_PATH, "../config.ini")

_config = ConfigParser.ConfigParser({
    "verbose": "False",
    "method": "usb",
    "i2c_device": "0",
})

_config.add_section("debug")
_config.add_section("device")

_config.read(CONFIG_PATH)

verbose = _config.getboolean("debug", "verbose")
method = _config.get("device", "method")
i2c_device = _config.getint("device", "i2c_device")

