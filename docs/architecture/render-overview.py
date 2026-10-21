"""Render the README overview: python render-overview.py (requires Pillow)."""
from pathlib import Path
from math import sin
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
SCALE = 2
W, H = 900, 1370
BG, INK, MUTED = '#F6F5F0', '#152A35', '#657577'
BLUE, CORAL, MINT = '#285FE8', '#F18462', '#BFE1CC'
im = Image.new('RGB', (W*SCALE, H*SCALE), BG)
d = ImageDraw.Draw(im)

def font(size, bold=False):
    name = 'BricolageGrotesque-Bold.ttf' if bold else 'InstrumentSans-Regular.ttf'
    return ImageFont.truetype(str(ROOT/'fonts'/name), round(size*SCALE))

def text(x, y, s, size=20, fill=INK, bold=False):
    d.text((x*SCALE, y*SCALE), s, font=font(size, bold), fill=fill, stroke_width=0)

def box(bounds, fill, radius=0, outline=None, width=1):
    d.rounded_rectangle(tuple(round(v*SCALE) for v in bounds), radius=radius*SCALE,
                        fill=fill, outline=outline, width=width*SCALE)

def line(points, fill, width=2):
    d.line([(round(x*SCALE), round(y*SCALE)) for x,y in points], fill=fill, width=width*SCALE)

def ellipse(bounds, fill):
    d.ellipse(tuple(round(v*SCALE) for v in bounds), fill=fill)

def poly(points, fill):
    d.polygon([(round(x*SCALE), round(y*SCALE)) for x,y in points], fill=fill)

def arrow(x, y, fill=BLUE):
    line([(x,y), (x,y+24)], fill, 2)
    poly([(x-5,y+19),(x+5,y+19),(x,y+26)], fill)

def step(n, y, title, sub):
    ellipse((46,y+3,78,y+35),INK)
    text(54,y+7,n,15,BG,True)
    text(94,y,title,27,INK,True)
    text(94,y+40,sub,18,MUTED)

def scene(bounds, bg, shirt, zoom=1):
    x,y,r,b = bounds
    box(bounds, bg, 12)
    # Abstract speaker and studio shapes, not a frame from an actual video.
    box((x+12,y+12,x+35,b-12),'#FFFFFF',5)
    line([(x+48,y+19),(r-13,y+19)], '#CBD6D4',2)
    cx=(x+r)/2; h=b-y; rw=(r-x)*.22*zoom
    ellipse((cx-rw,y+h*.47,rw+cx,b+h*.4),shirt)
    ellipse((cx-h*.12*zoom,y+h*.20,cx+h*.12*zoom,y+h*.44),'#EDBFA0')
    # Cover lower illustration overflow; surrounding canvas is always opaque.
    box((x,b,r,b+int(h*.4)+1),BG)

# Editorial header.
text(48,38,'CLIPPER',21,INK,True)
text(655,42,'HOW IT WORKS',14,MUTED)
line([(48,80),(852,80)],'#CED5D1',1)
text(46,101,'Long video.',62,INK,True)
text(46,164,'Short clips.',62,BLUE,True)
text(50,246,'Four steps. Three ways to find the story.',22,MUTED)

# 1 / Source, shown as a player rather than another prose box.
step('1',317,'Bring a video','YouTube or a local file')
scene((472,300,822,443),'#DCE8E3','#77938E')
box((472,413,822,443),INK,0)
poly([(489,423),(489,434),(499,428)],'#FFFFFF')
line([(512,428),(801,428)],'#607478',3)
line([(512,428),(610,428)],CORAL,3)
box((746,309,812,335),BG,7)
text(754,314,'VIDEO',12,INK,True)
arrow(646,455)
line([(48,492),(852,492)],'#DFE3DD',1)

# 2 / Speech timing is visible in waveform bars and aligned words.
step('2',535,'Read the signal','Speech, timing and scene cuts')
for i in range(54):
    x=470+i*6.5
    h=9+abs(sin(i*.61)*sin(i*.17+.8))*57
    box((x,570-h/2,x+3.5,570+h/2), BLUE if i<32 else '#B6C5D2',1)
for x,label,w in [(472,'Every',66),(545,'word',62),(614,'in',34),(655,'time.',67)]:
    box((x,615,x+w,645), '#E1E8FD' if label=='word' else '#EAEDE7',5)
    text(x+8,619,label,16,BLUE if label=='word' else INK)
arrow(646,660)
line([(48,700),(852,700)],'#DFE3DD',1)

# 3 / Branches are different visual operations, kept at equal weight.
step('3',731,'Find the moments','The mode fits the video')
for j,(label,sub,color) in enumerate([('Talks','Select',BLUE),('Trailers','Reorder',CORAL),('Visuals','Detect peaks','#477862')]):
    x=462+j*129
    box((x,731,x+119,844),'#ECEEE8',12)
    if j==0:
        for k in range(4):
            box((x+14,749+k*9,x+103,754+k*9),color if k in (1,2) else '#CCD4CD',2)
    elif j==1:
        for k, yy in enumerate([764,748,756]):
            box((x+15+k*30,yy,x+39+k*30,yy+22),color,4)
        line([(x+16,792),(x+99,792)],color,2)
        poly([(x+99,792),(x+92,788),(x+92,796)],color)
    else:
        line([(x+15,783),(x+31,775),(x+45,783),(x+61,748),(x+75,777),(x+100,766)],color,3)
    text(x+13,805,label,18,INK,True)
    text(x+10,854,sub,16,MUTED)
arrow(646,886)
line([(48,925),(852,925)],'#DFE3DD',1)

# 4 / Phone portraits demonstrate framing + captions + output in one glance.
step('4',960,'Make it vertical','Frame. Caption. Check.')
text(95,1050,'Clips + post text',20,INK,True)
text(95,1081,'Ready for your review',18,MUTED)
for j in range(3):
    x=466+j*130
    box((x,954,x+116,1177), INK,18)
    # Draw the portrait inside the phone, using its own clipped canvas.
    phone=Image.new('RGB',(104*SCALE,207*SCALE),'#DCE8E3')
    pd=ImageDraw.Draw(phone)
    pd.rectangle((11*SCALE,17*SCALE,24*SCALE,160*SCALE),fill='#C8D9D0')
    pd.ellipse((18*SCALE,88*SCALE,100*SCALE,243*SCALE),fill=['#6B8882','#A67E65','#5F7794'][j])
    pd.ellipse((43*SCALE,49*SCALE,75*SCALE,87*SCALE),fill='#EDBFA0')
    im.paste(phone,((x+6)*SCALE,962*SCALE))
    box((x+39,962,x+77,971),INK,4)
    box((x+14,1091,x+103,1120),INK,5)
    text(x+20,1095,['FIND YOUR','THE STORY','THAT NEXT'][j],12,'#FFFFFF',True)
    box((x+30,1126,x+88,1149),CORAL,4)
    text(x+35,1130,['MOMENT','STARTS','IDEA'][j],12,INK,True)
    text(x+33,1188,['9:16','9:16','9:16'][j],16,MUTED)

# Quiet footer keeps implementation details out of the primary reading path.
line([(48,1236),(852,1236)],'#CED5D1',1)
text(48,1256,'LOCAL TRANSCRIPTION & EDITING',14,MUTED,True)
text(48,1281,'AI assists selection and scoring.',17,INK)
text(48,1320,'Illustrative overview · mode details in the architecture guide',14,MUTED)
im.save(ROOT/'overview.png', optimize=True)
print(f'Rendered {ROOT / "overview.png"} ({W*SCALE} × {H*SCALE})')
