"""Plot k/m by target hand, one figure per hand size, from saved results."""
import json
import math
from pathlib import Path
from reportlab.graphics.shapes import Drawing, String, Line, Rect
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.widgets.markers import makeMarker
from reportlab.graphics import renderSVG
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'charts'
OUT.mkdir(exist_ok=True)
FONT='Microsoft YaHei'
pdfmetrics.registerFont(TTFont(FONT,'C:/Windows/Fonts/msyh.ttc'))
rows=json.loads((ROOT/'results.json').read_text(encoding='utf-8'))['records']
KINDS=['pair','two_pair','three','straight','flush','full_house','four','straight_flush']
LABELS=['一对','两对','三条','顺子†','同花','葫芦','四条','同花顺†']
lookup={(r['m'],r['j'],r['kind']):r for r in rows}
palette=['#2563EB','#D97706','#178575','#8B5CF6']
markers=['FilledCircle','FilledSquare','FilledDiamond','FilledTriangle']
YMIN=1.0
YMAX=round(math.ceil((max(r['k']/r['m'] for r in rows)+0.03)/0.2)*0.2,1)

def label(d,x,y,text,size=18,color='#334155',anchor='start'):
    d.add(String(x,y,text,fontName=FONT,fontSize=size,fillColor=colors.HexColor(color),textAnchor=anchor))

for m in range(6,11):
    d=Drawing(1100,540)
    d.add(Rect(0,0,1100,540,fillColor=colors.white,strokeColor=None))
    label(d,84,490,f'手牌数 m = {m}',30,'#172033')
    for j in range(1,5):
        x=420+(j-1)*153
        c=colors.HexColor(palette[j-1])
        d.add(Line(x,500,x+31,500,strokeColor=c,strokeWidth=3))
        marker=makeMarker(markers[j-1],x=x+15.5,y=500,size=8,fillColor=c,strokeColor=c)
        d.add(marker)
        label(d,x+42,493,f'j = {j}',21)
    p=LinePlot()
    p.x,p.y,p.width,p.height=90,112,946,322
    p.data=[[(i,lookup[m,j,kind]['k']/m) for i,kind in enumerate(KINDS)] for j in range(1,5)]
    p.joinedLines=1
    p.xValueAxis.valueMin=-0.12
    p.xValueAxis.valueMax=7.12
    p.xValueAxis.valueSteps=list(range(8))
    p.xValueAxis.labelTextFormat=lambda x:LABELS[int(round(x))]
    p.xValueAxis.labels.fontName=FONT
    p.xValueAxis.labels.fontSize=19
    p.xValueAxis.labels.fillColor=colors.HexColor('#334155')
    p.xValueAxis.labels.dy=-10
    p.xValueAxis.strokeColor=colors.HexColor('#AAB4C2')
    p.xValueAxis.tickDown=5
    p.yValueAxis.valueMin=YMIN
    p.yValueAxis.valueMax=YMAX
    p.yValueAxis.valueSteps=[round(1.0+0.2*i,1) for i in range(round((YMAX-YMIN)/0.2)+1)]
    p.yValueAxis.labelTextFormat='%0.1f'
    p.yValueAxis.labels.fontName=FONT
    p.yValueAxis.labels.fontSize=18
    p.yValueAxis.labels.fillColor=colors.HexColor('#475569')
    p.yValueAxis.labels.dx=-10
    p.yValueAxis.strokeColor=colors.HexColor('#AAB4C2')
    p.yValueAxis.tickLeft=4
    p.yValueAxis.visibleGrid=1
    p.yValueAxis.gridStrokeColor=colors.HexColor('#E4E9EF')
    p.yValueAxis.gridStrokeWidth=0.7
    for j in range(4):
        c=colors.HexColor(palette[j])
        p.lines[j].strokeColor=c
        p.lines[j].strokeWidth=2.8
        p.lines[j].symbol=makeMarker(markers[j],size=8,fillColor=c,strokeColor=c)
    d.add(p)
    label(d,88,449,'k/m',19,'#475569')
    label(d,563,52,'牌型',19,'#475569','middle')
    label(d,84,17,'† 顺子、同花顺：j=1 为最优策略的抽样估计；j≥2 为近似策略。',15,'#64748B')
    renderSVG.drawToFile(d,str(OUT/f'ratio-m{m}.svg'))
print(f'Created five charts with shared y range [{YMIN}, {YMAX}]')
