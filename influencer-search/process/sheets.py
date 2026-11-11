"""Contact sheets of review images, 4 per sheet, for fast review. usage: python -I sheets.py <outdir> h1 h2 ..."""
import os, sys
from PIL import Image, ImageDraw
out, hs = sys.argv[1], sys.argv[2:]
os.makedirs(out, exist_ok=True)
W, H = 1280, 500
for i in range(0, len(hs), 4):
    sheet = Image.new('RGB', (W * 2, (H + 30) * 2), 'white')
    d = ImageDraw.Draw(sheet)
    for j, h in enumerate(hs[i:i + 4]):
        p = os.path.join(os.path.dirname(__file__), 'review', h + '.jpg')
        if not os.path.exists(p): continue
        x, y = (j % 2) * W, (j // 2) * (H + 30) + 30
        sheet.paste(Image.open(p).convert('RGB').resize((W, H)), (x, y))
        d.rectangle([x, y - 30, x + W, y], fill='black')
        d.text((x + 10, y - 25), '%d. %s' % (j + 1, h), fill='yellow')
    sheet.resize((sheet.width * 3 // 5, sheet.height * 3 // 5)).save(os.path.join(out, 's%02d.jpg' % (i // 4)), quality=72)
print(len(hs), 'in', (len(hs) + 3) // 4, 'sheets')
