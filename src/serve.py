import locale

from flask import Flask, request
from PIL import Image, ImageDraw, ImageFont

from cnc_packet import build_upload_gif

from shutil import move

# set the project root directory as the static folder, you can set others.
app = Flask(__name__, static_url_path='')

OUT_HEIGHT = 17
THIS_PATH = os.path.dirname(os.path.realpath(__file__))
FONT_PATH = os.path.join(THIS_PATH, "../fonts")

@app.route('/paypal')
def serve_paypal():
    return app.send_static_file('index.html')


@app.route('/getgif')
def create_and_serve_pic():

    f = open('amount.txt', 'rb')
    amount = int(f.read())

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

    img_name = str(amount) + '.png'
    img.save('../images/' + img_name)
    print '../images/' + img_name

    # Convert to gif
    gif_name = str(amount) + '.gif'

    build_upload_gif(134, 330, img_name, './static/' + gif_name, clut_offset=17, sdram_offset=0x1000>>6, tile=1)

    # move('../images/' + gif_name, '/static/' + gif_name)
    print gif_name
    return app.send_static_file(gif_name)

if __name__ == "__main__":
    app.run(host='0.0.0.0')
