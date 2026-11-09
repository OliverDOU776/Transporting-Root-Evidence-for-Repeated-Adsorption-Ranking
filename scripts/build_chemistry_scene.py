"""Build the project page's native SVG application illustration.

The pore network is a schematic, not a reconstructed crystal. Gas molecules
use conventional atom colors and are illustrative, not simulation positions.
"""
from pathlib import Path
from math import cos, sin, radians

ROOT = Path(__file__).resolve().parents[1]
parts = ['''<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="350" viewBox="0 0 1100 350" role="img" aria-labelledby="title desc">
<title id="title">Repeated adsorption screening</title><desc id="desc">Schematic porous framework with linear carbon dioxide and diatomic nitrogen molecules. The same curve pool is queried at different pressures and feed compositions, reusing numerical root evidence.</desc>
<defs>
<radialGradient id="metal" cx="32%" cy="27%"><stop stop-color="#c1ddd8"/><stop offset=".6" stop-color="#589e95"/><stop offset="1" stop-color="#356a66"/></radialGradient>
<radialGradient id="carbon" cx="30%" cy="25%"><stop stop-color="#8c969f"/><stop offset="1" stop-color="#303940"/></radialGradient>
<radialGradient id="oxygen" cx="30%" cy="25%"><stop stop-color="#f2b7ad"/><stop offset="1" stop-color="#bb5b51"/></radialGradient>
<radialGradient id="nitrogen" cx="30%" cy="25%"><stop stop-color="#aec9e6"/><stop offset="1" stop-color="#527fae"/></radialGradient>
</defs><rect width="1100" height="350" fill="white"/>
''']
def text(x,y,s,size=16,fill='#485660',weight='400'):
    parts.append(f'<text x="{x}" y="{y}" font-family="Arial,Helvetica,sans-serif" font-size="{size}" fill="{fill}" font-weight="{weight}">{s}</text>')
def line(x1,y1,x2,y2,stroke='#bdcdd2',w=3,opacity=1):
    parts.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{w}" stroke-linecap="round" opacity="{opacity}"/>')
def sphere(x,y,r,fill,opacity=1):
    parts.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="url(#{fill})" opacity="{opacity}"/>')
def molecule(x,y,angle,gas,scale=1):
    parts.append(f'<g transform="translate({x} {y}) rotate({angle}) scale({scale})">')
    if gas=='co2':
        for yy in [-2.8,2.8]:line(-24,yy,24,yy,'#a7a9a8',2.2)
        sphere(-27,0,10,'oxygen');sphere(0,0,9.5,'carbon');sphere(27,0,10,'oxygen')
    else:
        for yy in [-3.5,0,3.5]:line(-10,yy,10,yy,'#839bb6',1.6)
        sphere(-14,0,10,'nitrogen');sphere(14,0,10,'nitrogen')
    parts.append('</g>')
# Two projected pore layers; topology only, no chemical identity is asserted.
pts={}
for z in [1,0]:
    for j in range(3):
        for i in range(3):pts[i,j,z]=(104+i*104+z*58,77+j*88-z*31)
for z in [1,0]:
    for j in range(3):
        for i in range(3):
            x,y=pts[i,j,z]
            for key in [(i+1,j,z),(i,j+1,z),(i,j,1) if z==0 else (-1,-1,-1)]:
                if key in pts:
                    xx,yy=pts[key];line(x,y,xx,yy,'#b3c7cb',4,.50 if z else .90)
for key,(x,y) in pts.items():sphere(x,y,7.5,'metal',.63 if key[2] else 1)
for vals in [(64,130,-25,'co2',1),(204,136,22,'co2',.78),(306,204,-35,'co2',.82),(394,83,-18,'co2',.74),(171,280,-18,'co2',.77),(91,301,14,'n2',.92),(349,133,35,'n2',.82),(278,67,-17,'n2',.73),(432,250,-20,'n2',.86),(211,218,14,'n2',.68)]:molecule(*vals)
text(64,332,'Porous adsorbent · schematic',12,'#7c8b94')
line(511,47,511,299,'#e2e8eb',1)
text(564,80,'One curve pool.',30,'#2d3840','600')
text(564,119,'Many operating conditions.',30,'#2d3840','600')
text(564,159,'Reuse a root enclosure from an earlier query',17)
text(564,185,'to avoid unnecessary numerical evaluations.',17)
# Gas context: explicit atom colors and conventional molecular forms.
molecule(590,236,0,'co2',.55);text(624,241,'CO₂',15,'#8b4b42')
molecule(730,236,0,'n2',.55);text(758,241,'N₂',15,'#4c739c')
text(564,294,'Pressure + feed → ranked adsorption candidates',16,'#28756f')
parts.append('</svg>')
(ROOT/'docs/assets/adsorption-scene.svg').write_text('\n'.join(parts)+'\n')

svg = (ROOT/'docs/assets/adsorption-scene.svg').read_text()
(ROOT/'docs/assets/adsorption-scene-mobile.svg').write_text(svg.replace('width="1100" height="350" viewBox="0 0 1100 350"', 'width="500" height="350" viewBox="20 0 460 350"'))
