#!/usr/bin/python2

import locale
import os

from flask import Flask, request, send_from_directory
from PIL import Image, ImageDraw, ImageFont
from tempfile import mkstemp

from cnc_packet import build_upload_gif

from shutil import move

# set the project root directory as the static folder, you can set others.
app = Flask(__name__, static_url_path='')

OUT_HEIGHT = 17
THIS_PATH = os.path.dirname(os.path.realpath(__file__))
FONT_PATH = os.path.join(THIS_PATH, "../fonts")
STATIC_PATH = os.path.join(THIS_PATH, "../static")

@app.route('/paypal')
def serve_paypal():
    return app.send_static_file('index.html')


@app.route('/getgif')
def create_and_serve_pic():

    f = open('amount.txt', 'rb')
    amount = int(f.read())

    gif_name = str(amount) + '.gif'
    if not os.path.isfile(os.path.join(STATIC_PATH, gif_name)):
        # Format number
        locale.setlocale(locale.LC_ALL, '')
        formatted_num = locale.currency(amount, grouping=True) + " USD"

        # Generate pic
        img = Image.new('RGB', (500, 500), (255, 255, 255))
        fnt = ImageFont.truetype(os.path.join(FONT_PATH, 'arialbd.ttf'), 25)
        # get a drawing context
        d = ImageDraw.Draw(img)
        # draw text, half opacity
        d.text((1, 0), formatted_num, font=fnt, fill=(51, 51, 51))
        # Crop to text
        (txt_width, txt_height) = d.textsize(formatted_num, font=fnt)
        print txt_height, txt_width
        # if txt_width % 2 == 0
        img = img.crop((0, 0, 300, 26))
        # else:
            # img = img.crop((0, 0, txt_width+1, 26))

        # print "width, height" + str(width) + ", " + str(height)

        baseheight = OUT_HEIGHT
        hpercent = (baseheight / float(img.size[1]))
        wsize = int((float(img.size[0]) * float(hpercent)))
        img = img.resize((wsize, baseheight), Image.ANTIALIAS)

        f, img_name = mkstemp(suffix='.png')
        os.close(f)
        img.save(img_name)

        # Convert to gif
        build_upload_gif(134, 330, img_name, os.path.join(STATIC_PATH, gif_name),
                         clut_offset=17, sdram_offset=0x1000>>6, tile=1)

    return send_from_directory(STATIC_PATH, gif_name)

if __name__ == "__main__":
    app.run(host='0.0.0.0')
