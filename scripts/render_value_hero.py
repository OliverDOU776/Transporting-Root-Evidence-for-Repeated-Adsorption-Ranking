"""Render the opening value animation from native drawing primitives.

Run: python scripts/render_value_hero.py
No browser, network, or model API is needed. The chemistry and process drawings
are schematic. The small exclusion is exact arithmetic; the final paid timings
come from the repository's measured CRAFTED workload. Animation speed is not
execution time. All assets and a provenance manifest are written under docs/media.
"""
from __future__ import annotations
import argparse
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import subprocess
import tempfile

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / 'docs' / 'media'
W, H, DURATION = 1280, 660, 20
INK='#303d46'; SOFT='#657580'; RULE='#dce5e9'; BLUE='#3978a7'; TEAL='#227d75'; RED='#bd6661'; NBLUE='#5a80b0'; PALE='#f2f6f8'; GREEN='#e9f5ef'; AMBER='#a8773b'
FONT_DIR=Path('/usr/share/fonts/truetype/liberation')
FONTS={}


def ease(v):
    v=max(0., min(1.,v)); return v*v*(3-2*v)
def mix(a,b,t): return a+(b-a)*t

def font(size,bold=False):
    key=(size,bold)
    if key not in FONTS:
        p=FONT_DIR/('LiberationSans-Bold.ttf' if bold else 'LiberationSans-Regular.ttf')
        FONTS[key]=ImageFont.truetype(str(p),size)
    return FONTS[key]

class Art:
    def __init__(self):
        self.im=Image.new('RGB',(W,H),'white');self.d=ImageDraw.Draw(self.im)
    def text(self,x,y,s,size=24,fill=INK,bold=False,anchor='la'):
        self.d.text((x,y),s,font=font(size,bold),fill=fill,anchor=anchor)
    def box(self,x,y,w,h,fill='white',stroke=RULE,r=10,sw=2):
        self.d.rounded_rectangle((x,y,x+w,y+h),r,fill=fill,outline=stroke,width=sw)
    def line(self,pts,color=RULE,width=3):self.d.line(pts,fill=color,width=width,joint='curve')
    def arrow(self,pts,color=SOFT,width=3,head=11):
        self.line(pts,color,width);(x0,y0),(x,y)=pts[-2:];a=math.atan2(y-y0,x-x0)
        self.d.polygon([(x,y),(x-head*math.cos(a-.43),y-head*math.sin(a-.43)),(x-head*math.cos(a+.43),y-head*math.sin(a+.43))],fill=color)
    def dashed(self,x1,y1,x2,y2,color=SOFT,width=2):
        L=math.hypot(x2-x1,y2-y1)
        if not L:return
        for start in range(0,int(L),12):
            e=min(L,start+6);self.line([(mix(x1,x2,start/L),mix(y1,y2,start/L)),(mix(x1,x2,e/L),mix(y1,y2,e/L))],color,width)
    def check(self,x,y,r=12,color=TEAL):
        self.d.ellipse((x-r,y-r,x+r,y+r),fill=color)
        self.line([(x-r*.5,y),(x-r*.08,y+r*.37),(x+r*.55,y-r*.4)],'white',3)
    def mol(self,x,y,gas='co2',s=1,angle=0):
        co=math.cos(angle);si=math.sin(angle)
        offs=[-16,0,16] if gas=='co2' else [-8,8]
        centers=[(x+v*s*co,y+v*s*si) for v in offs]
        self.line(centers,INK,max(2,int(3*s)))
        for i,(cx,cy) in enumerate(centers):
            c=(RED if i!=1 else '#495862') if gas=='co2' else NBLUE
            rr=8*s
            self.d.ellipse((cx-rr,cy-rr,cx+rr,cy+rr),fill=c,outline=INK,width=1)
            self.d.ellipse((cx-rr*.5,cy-rr*.6,cx-rr*.05,cy-rr*.16),fill='#e7ebed')
    def pore(self,x,y,w=108,h=88,label=None,selected=False):
        self.box(x,y,w,h,'#d7eae5',TEAL,r=13,sw=3 if selected else 2)
        for row in range(2):
            for col in range(3):
                self.box(x+10+col*(w-15)/3,y+12+row*(h-20)/2,(w-33)/3,(h-35)/2,'#fafdfd','#82b2a8',r=5,sw=2)
        if label:self.text(x+w/2,y+h+9,label,21,TEAL if selected else SOFT,True,'ma')
    def gear(self,x,y,t,r=29,color=SOFT):
        for n in range(10):
            a=math.pi*2*n/10+t
            self.line([(x+math.cos(a)*(r-5),y+math.sin(a)*(r-5)),(x+math.cos(a)*(r+5),y+math.sin(a)*(r+5))],color,6)
        self.d.ellipse((x-r+5,y-r+5,x+r-5,y+r-5),outline=color,width=6)
        self.d.ellipse((x-6,y-6,x+6,y+6),fill=color)
    def packet(self,x,y,label,color=TEAL):
        self.box(x-19,y-17,38,34,'white',color,r=7,sw=2)
        self.text(x,y-11,label,20,color,True,'ma')


def factory(c,x,y):
    c.d.polygon([(x,y+74),(x+31,y+54),(x+31,y+74),(x+61,y+54),(x+61,y+74),(x+114,y+74),(x+114,y+167),(x,y+167)],fill='#6e808d',outline=INK,width=3)
    c.d.polygon([(x+63,y+74),(x+70,y-4),(x+92,y-4),(x+101,y+74)],fill='#6e808d',outline=INK,width=3)
    c.box(x+67,y-10,29,11,'#485965',INK,r=2)
    c.line([(x+71,y+13),(x+93,y+13)],RED,6)
    for n in range(3):c.box(x+13+n*32,y+99,21,30,'#faf4e4',INK,r=3,sw=2)
    c.line([(x-10,y+169),(x+124,y+169)],INK,3)


def curves(c,x,y,w=230,h=85):
    c.line([(x,y),(x,y+h),(x+w,y+h)],'#aab9c2',2)
    for row,clr in [(0,TEAL),(1,NBLUE)]:
        pts=[]
        for k in range(60):
            z=k/59; yy=z*(h-8)*(0.5 if not row else 1.0)
            pts.append((x+z*w,y+h-yy))
        c.line(pts,clr,3)
    c.text(x,y+h+6,'Stored pure-gas curves',17,SOFT)


def caption(c,s):
    c.d.rectangle((0,590,W,H),fill='#eef3f6')
    c.line([(0,590),(W,590)],RULE,2)
    c.text(W/2,611,s,27,INK,True,'ma')


def progress(c,scene,t):
    for n in range(5):
        c.d.ellipse((1140+n*23,24,1149+n*23,33),fill=TEAL if n==scene else '#dce5e9')
    c.d.rectangle((0,H-3,int(W*t/DURATION),H),fill='#71a99f')


def chemical_scene(c,t):
    c.text(40,28,'Which material keeps CO₂ and lets N₂ pass?',31,bold=True)
    factory(c,70,237)
    c.text(130,201,'CO₂ + N₂ feed',23,SOFT,True,'ma')
    for k in range(7):
        u=((t*.23+k/7)%1)
        x=204+u*285;y=268+(k%4)*37+math.sin(u*6.28+k)*8
        c.mol(x,y,'co2' if k%2==0 else 'n2',1.,math.sin(k)*.18)
    c.arrow([(226,438),(458,438)],'#9baeb9',3)
    positions=[(505,172),(662,172),(505,345),(662,345)]
    for (x,y),label in zip(positions,['A','B','C','D']):
        c.pore(x,y,125,104,label)
        c.mol(x+36,y+28,'co2',.75)
    c.text(646,115,'Adsorption candidates',25,bold=True,anchor='ma')
    c.arrow([(818,300),(904,300)],BLUE,3)
    c.box(945,182,260,252,'#f6fafb',RULE)
    c.text(1075,202,'Rank the candidates',25,bold=True,anchor='ma')
    for i,label in enumerate(['A','C','D']):
        c.text(972,255+i*53,str(i+1),21,SOFT)
        c.box(1005,246+i*53,166,36,'white','#b9d4d0',r=6)
        c.text(1020,253+i*53,'Candidate '+label,21,TEAL,True)
    c.check(1075,473,17)
    c.text(1075,504,'A useful shortlist',23,TEAL,True,'ma')
    c.text(40,553,'Schematic chemistry and candidate labels',17,SOFT)
    caption(c,'Find the best material for CO₂ capture.')


def input_pool(c,t):
    c.text(158,115,'The same candidate pool',23,bold=True,anchor='ma')
    for k,(x,y) in enumerate([(47,170),(178,170),(47,306),(178,306)]):
        c.pore(x,y,98,78,['A','B','C','D'][k],selected=k==1)
    curves(c,48,443,225,69)
    c.mol(67,86,'co2',.72);c.text(96,75,'CO₂',20,SOFT)
    c.mol(194,86,'n2',.72);c.text(221,75,'N₂',20,SOFT)
    c.line([(316,120),(316,550)],RULE,2)


def engine(c,t,stage):
    title={1:'New pressure. The same screening question.',2:'Can this candidate still enter the shortlist?',3:'Rule it out first. Refine only the rest.'}[stage]
    c.text(40,28,title,31,bold=True)
    input_pool(c,t)
    p_change=ease((t-3.7)/1.9)
    c.box(365,83,417,52,PALE,RULE)
    pval=1+.1*p_change
    if stage==1:c.text(386,96,f'Pressure  1.00  →  {pval:.2f}',25,BLUE,True)
    else:c.text(386,96,'New pressure 1.10 · same feed',24,BLUE,True)
    c.text(819,101,'Analytic illustration',18,SOFT)
    # A query-local fresh numerical test is depicted without claiming that every
    # candidate is solved by LeanCap (which has its own cap-based exclusions).
    c.text(377,162,'Without stored root evidence',24,SOFT,True)
    c.packet(383,247,'B',SOFT)
    c.arrow([(409,247),(562,247)],'#a5b4bc',3)
    c.box(575,198,180,112,'#f7f9fa',RULE)
    c.gear(617,246,t*.6,22,SOFT)
    c.text(651,221,'Fresh',23,SOFT,True)
    c.text(651,250,'test',23,SOFT,True)
    c.arrow([(770,247),(917,247)],'#a5b4bc',3)
    # In the reuse lane the source sheet is present, then the transformed bound.
    c.text(377,340,'Reuse the previous solve',24,TEAL,True)
    c.box(366,379,167,133,'#f0f8f5','#9cc4bb',r=8)
    c.text(449,393,'Previous solve',22,TEAL,True,'ma')
    c.text(449,426,'Score = 0.50',24,INK,True,'ma')
    c.text(449,459,'Root bracket saved',16,TEAL,False,'ma')
    c.line([(394,480),(503,480)],'#9ab4ad',2)
    c.line([(432,480),(466,480)],TEAL,7)
    c.d.ellipse((445,475,454,484),fill=TEAL)
    c.arrow([(545,445),(587,445)],TEAL,3)
    c.box(599,370,294,156,'white','#9cc4bb',r=9)
    c.text(746,382,'Bound at the new pressure',21,TEAL,True,'ma')
    if stage==1:
        c.text(746,430,'Reuse the stored solve',23,SOFT,False,'ma')
        c.text(746,467,'before a new numerical test',20,SOFT,False,'ma')
    else:
        c.text(746,422,'Score ≤ 0.58 < 1.00 needed',22,TEAL,True,'ma')
        # Exact upper bound 11/19; cutoff 1.0 on a shared zero-based score scale.
        x0=625;length=237;lim=1.15
        c.line([(x0,480),(x0+length,480)],'#c8d5db',2)
        upper=x0+length*float(Fraction(11,19))/lim;cut=x0+length/lim
        c.line([(x0,475),(upper,475)],TEAL,11)
        c.dashed(cut,457,cut,493,AMBER,2)
        c.text(x0,492,'0',16,SOFT)
        c.text(cut,494,'cutoff',16,AMBER,False,'ma')
    c.box(945,183,284,147,'#f6fafb',RULE)
    c.text(1087,200,'Shortlist',25,bold=True,anchor='ma')
    for i,label in enumerate(['A','C','D']):
        c.box(966,239+i*25,242,21,'white','#cbdcdd',r=4,sw=1)
        c.text(982,240+i*25,f'{i+1}   Candidate {label}',17,TEAL)
    if stage>=2:
        c.arrow([(906,445),(1184,445)],TEAL,4)
        c.check(1012,445,17)
        c.text(1083,470,'Exclude B. Skip its solve.',21,TEAL,True,'ma')
    if stage>=3:
        # An unresolved candidate still routes to a fresh test; do not imply
        # that the entire new query is free of numerical work.
        c.dashed(552,359,552,280,SOFT)
        c.arrow([(552,280),(573,280)],SOFT,2)
        c.packet(552,328,'C',SOFT)
        c.text(772,326,'Unresolved? Test it.',18,SOFT,False,'ma')
        c.check(1206,203,13)
        c.text(1088,365,'Same ranked answer',22,TEAL,True,'ma')
    # Packet movement makes the avoided numerical work visible.
    if stage==1:
        u=((t-3.6)/2.6)%1
        c.packet(mix(411,560,u),247,'B',SOFT)
        # Reuse visibly carries the saved bracket into the new condition.
        u=ease((t-4.3)/2.1)
        if 0<u<1:
            xx=mix(500,706,u)
            c.line([(xx-18,481),(xx+18,481)],TEAL,7)
    elif stage==2:
        u=ease((t-7.0)/2.7)
        # B bypasses the test at y=247: right, then up to the ranked output.
        xx=mix(908,1165,u);yy=445
        if u<1:c.packet(xx,yy,'B',TEAL)
        # Visually mark its candidate tile as excluded, not a lost answer.
        c.dashed(180,210,274,210,TEAL,3)
    elif stage==3:
        u=ease((t-11.0)/2.8)
        if u<.30:xx=552;yy=mix(350,280,u/.30)
        elif u<.60:xx=mix(552,575,(u-.30)/.30);yy=280
        else:xx=mix(770,917,(u-.60)/.40);yy=247
        if u<1:c.packet(xx,yy,'C',SOFT)
        c.dashed(180,210,274,210,TEAL,3)
    c.text(40,553,'Illustration: q₁(p) = p, q₂(p) = 2p; equal feed. Cutoff from an eligible candidate.',17,SOFT)
    if stage==1:caption(c,'Pressure changes. The curves stay. The ranking must be updated.')
    elif stage==2:caption(c,'Its score cannot reach the cutoff. Skip the expensive solve.')
    else:caption(c,'Test only what the old evidence cannot rule out.')


def results_scene(c,t,bench):
    c.text(40,28,'Same ranked answer. Less repeated work.',32,bold=True)
    c.text(40,88,'Representative CRAFTED CO₂/N₂ workload',25,SOFT)
    c.text(40,124,'64 nearby top-1 queries · 16,010 configuration pairs',23,SOFT)
    # The answer icons are schematic. Timed bars encode the actual medians.
    c.pore(88,244,133,119,None,True)
    c.text(154,385,'Same winner',26,TEAL,True,'ma')
    c.check(153,445,24)
    c.arrow([(249,303),(350,303)],'#91aca6',4)
    x0=566;span=530;maxsec=6.0
    for y,lab,val,col in [(247,'LeanCap',bench['lean'], '#778895'),(384,'Transport',bench['transport'], TEAL)]:
        c.text(382,y+8,lab,28,col,True)
        end=x0+span*val/maxsec*ease((t-14.8)/1.1)
        c.box(x0,y,max(1,end-x0),48,col,col,r=6,sw=1)
        c.text(x0+span*val/maxsec+18,y+6,f'{val:.2f} s',31,col,True)
    c.line([(x0,475),(x0+span,475)],'#b6c6ce',2)
    for v in [0,2,4,6]:
        xx=x0+span*v/maxsec;c.line([(xx,470),(xx,482)],'#b6c6ce',2);c.text(xx,489,str(v)+' s',19,SOFT,False,'ma')
    c.text(382,547,'Paid lifecycle: setup + acquisition + queries + teardown.',21,SOFT)
    caption(c,'About half the paid time in this repeated-query workload.')


def frame(t,bench):
    c=Art()
    stage=0 if t<3.6 else 1 if t<6.8 else 2 if t<10.8 else 3 if t<14.8 else 4
    # Smooth crossfades occur only at narrative changes; molecules and gears
    # move continuously within scenes. Candidate identities remain consistent.
    if stage==0:chemical_scene(c,t)
    elif stage<4:engine(c,t,stage)
    else:results_scene(c,t,bench)
    progress(c,stage,t)
    return c.im


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--fps',type=int,default=15)
    ap.add_argument('--keyframes-only',action='store_true')
    args=ap.parse_args()
    source=json.loads((ROOT/'docs/media/root-transport-data.json').read_text())
    assert Fraction(source['score_upper'])==Fraction(11,19)<Fraction(source['score_cut'])
    results=json.loads((ROOT/'evidence/published_results.json').read_text())
    example=results['example']
    # Read the recorded descriptive arm medians, never infer times from the cartoon.
    print(json.dumps(example,indent=2))
    # Stable keys in the distributed result table.
    bench={'transport':example['Transport']['median_paid_seconds'],'lean':example['LeanCap']['median_paid_seconds']}
    MEDIA.mkdir(parents=True,exist_ok=True)
    keytimes=[1.5,5.2,8.9,12.5,17.2]
    keydir=ROOT/'tmp'/'value-hero';keydir.mkdir(parents=True,exist_ok=True)
    for i,t in enumerate(keytimes):frame(t,bench).save(keydir/f'scene-{i+1}.png',optimize=True)
    frame(12.5,bench).quantize(colors=256).save(MEDIA/'value-hero-poster.png',optimize=True)
    if not args.keyframes_only:
        ff=['ffmpeg','-y','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(args.fps),'-i','-','-an','-c:v','libx264','-threads','2','-preset','medium','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(MEDIA/'value-hero.mp4')]
        p=subprocess.Popen(ff,stdin=subprocess.PIPE)
        prev=None
        try:
            for n in range(args.fps*DURATION):
                t=n/args.fps
                im=frame(t,bench)
                # Short semantic crossfades, not independent title slides.
                for boundary in [3.6,6.8,10.8,14.8]:
                    if boundary<=t<boundary+.23:
                        before=frame(boundary-.001,bench)
                        im=Image.blend(before,im,ease((t-boundary)/.23))
                p.stdin.write(im.tobytes())
        finally:p.stdin.close()
        if p.wait():raise RuntimeError('Video encoding failed')
        filters='fps=10,scale=960:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=192[p];[b][p]paletteuse=dither=bayer:bayer_scale=4'
        subprocess.run(['ffmpeg','-y','-v','error','-threads','2','-i',str(MEDIA/'value-hero.mp4'),'-filter_complex_threads','1','-filter_complex',filters,'-loop','0',str(MEDIA/'value-hero.gif')],check=True)
    story={
        'title':'Same ranked answer. Less repeated work.',
        'duration_seconds':DURATION,'size':[W,H],'fps':args.fps,
        'scope':'Molecular drawings, candidate labels, routes and shortlist are schematic. The Henry bound is exact arithmetic, not an experimental CO2/N2 isotherm. The final paid times are a separate measured workload. Animation pacing is not execution time.',
        'analytic_source':'root-transport-data.json','analytic_example':source,
        'measured_source':'../../evidence/published_results.json#example',
        'measured_workload':example,
        'bound_score_upper_exact':'11/19','bound_score_upper_display':'0.58', 'bound_note':'Conservative upper bound, not a sharp maximum; actual analytic score remains 1/2.','eligible_cutoff':'1.00',
        'scenes':[{'start':t,'title':s} for t,s in [(0,'Screen adsorption candidates'),(3.6,'Change pressure; keep the curves'),(6.8,'Transport evidence and exclude a candidate'),(10.8,'Refine unresolved candidates'),(14.8,'Measured repeated-query payoff')]],
        'author':'Zijia Wang',
        'files':{}
    }
    for name in ['value-hero.mp4','value-hero.gif','value-hero-poster.png']:
        path=MEDIA/name
        if path.exists():story['files'][name]={'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    (MEDIA/'value-hero-data.json').write_text(json.dumps(story,indent=2)+'\n')

if __name__=='__main__':main()
