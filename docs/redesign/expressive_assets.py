"""Original editable vector studies for the proposed expressive layer.

No third-party artwork, runtime assets, or application code is imported.
SVGs are documentation masters; Android delivery needs Canvas or reviewed PNGs.
"""
from pathlib import Path
import math,json,hashlib
R=Path(__file__).resolve().parent
P='var(--brand,#123D32)'; A='var(--accent,#F4B78A)'; W='var(--wash,#CFF6DC)'; I='var(--ink,#172520)'; S='var(--paper,#FFFFFF)'
def rect(x,y,w,h,fill=P,rx=8,extra=''):return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" {extra}/>'
def circle(x,y,r,fill=P,extra=''):return f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" {extra}/>'
def path(d,stroke=P,width=3,fill='none',extra=''):return f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round" {extra}/>'
def group(content,layer,anim=''):return f'<g data-layer="{layer}" data-anim="{anim}">{content}</g>'
def star(x,y,r=24,n=8,fill=A):
 points=[]
 for j in range(n*2):
  radius=r if j%2==0 else r*.58;a=j*math.pi/n-math.pi/2
  points.append(f'{x+radius*math.cos(a):.2f},{y+radius*math.sin(a):.2f}')
 return '<polygon points="'+' '.join(points)+f'" fill="{fill}"/>'
def car(outline=False):
 fill='none' if outline else P
 body=path('M59 154l18-39q4-8 15-8h82q9 0 16 8l29 36 23 7q8 3 8 12v17H49v-20q0-8 10-13Z',P,3,fill)
 body+=path('M88 117h36v32H74Z',I,1.5,S)+path('M134 117h37l28 32h-65Z',I,1.5,S)
 body+=rect(204,166,29,8,A,4)+rect(55,166,13,8,A,3)+rect(116,98,34,10,A,4)
 for x in [91,208]:body+=group(circle(x,187,19,I)+circle(x,187,10,S)+path(f'M{x-6} 187h12M{x} 181v12',P,2),f'wheel-{x}','wheel')
 body+=path('M132 156v25M146 160h12',S if not outline else P,2)
 return group(body,'taxi','taxi')
def city(line=False):
 out=''
 for j,(x,y,w,h) in enumerate([(38,87,48,87),(94,47,61,127),(164,73,42,101),(213,97,62,77)]):
  fill='none' if line else (W if j%2==0 else A)
  out+=rect(x,y,w,h,fill,5,f'stroke="{P}" stroke-width="2"')
  for yy in range(y+14,y+h-12,19):out+=path(f'M{x+10} {yy}h{w-20}',P,2)
 out+=path('M97 47l8-12h40l9 12M21 175h278',P,2)
 return group(out,'city','city')
def paper(x=99,y=48,w=124,h=148):return rect(x,y,w,h,S,13,f'stroke="{P}" stroke-width="3"')
def lines(x=122,y=84,width=68):return ''.join(path(f'M{x} {y+j*20}h{width if j<2 else width*.6}',P,4) for j in range(3))
ART={}
def put(key,name,content,purpose):ART[key]=dict(id=key,name=name,content=content,purpose=purpose)
put('G01','City in layers',group(circle(226,58,33,A),'sun','float')+city()+path('M15 192q77-28 150 0t143 0',P,5)+car(),'Welcome and idle city identity; geometric Art Deco rhythm, not a literal city map.')
put('G02','Illustrated taxi',group(circle(155,118,91,W),'backplate')+car(),'Friendly original silhouette with separated windows, body, wheels and roof light.')
put('G03','City linework',city(True)+path('M21 193h275M52 211h216',P,2)+group(circle(258,41,16,'none',f'stroke="{P}" stroke-width="2"'),'sun','float'),'Editorial architectural line drawing for compact city headers.')
put('G04','Route ribbon',group(path('M38 171C70 170 79 44 135 61S175 184 236 134s42-79 61-75',W,28)+path('M38 171C70 170 79 44 135 61S175 184 236 134s42-79 61-75',P,13,extra='pathLength="1" data-draw="true"'),'ribbon','draw')+circle(38,171,11,S,f'stroke="{P}" stroke-width="4"')+rect(285,47,24,24,A,6),'Abstract brand route emblem; actual directions remain separate server geometry.')
ticket=paper(69,44,184,159)+lines(101,86,102)+path('M85 156h152',P,2,extra='stroke-dasharray="4 6"')
for yy in [78,122,165]:ticket+=circle(69,yy,7,W)+circle(253,yy,7,W)
put('G05','Journey ticket',group(ticket,'ticket','ticket'),'Receipt/trip-history framing, perforations outside text and totals.')
put('G06','Sunburst accent',group(star(161,120,85,10,P),'sunburst','rotate')+circle(161,120,39,W)+path('M142 119h38M160 100v38',P,5),'A decorative chapter marker; carries no verified/eligible meaning.')
arches=''
for j in range(5):arches+=path(f'M{45+j*24} 193V{101+j*4}a{115-j*24} {89-j*15} 0 0 1 {230-j*48} 0v{92-j*4}',P if j%2==0 else A,12)
put('G07','Architectural arch',group(arches,'arch','city'),'Streamline architectural framing on welcome/account headers.')
tiles=''
for y in range(45,194,37):
 for x in range(75,224,37):tiles+=path(f'M{x} {y-14}l14 14-14 14-14-14Z',P,2, A if (x+y)%2==0 else W)
put('G08','Geometric corner tile',group(tiles,'tiles','reveal'),'Original geometric motif inspired by local visual rhythm, with large breathing room.')
waves=''.join(path(f'M20 {110+j*28}q35-28 70 0t70 0t70 0t70 0',P if j==1 else A,11) for j in range(3))
put('G09','Atlantic wave',group(circle(160,53,25,A),'sun','float')+group(waves,'wave','wave'),'A cropped horizon ornament with a calm finite drift.')
key=circle(113,83,35,'none',f'stroke="{P}" stroke-width="13"')+path('M139 110l79 79 18-18-18-18 12-12-16-16-12 12-33-33',P,17)+rect(65,123,54,69,A,15)+path('M80 152h24M81 165h18',P,4)
put('G10','Taxi keyring',group(key,'keys','sway'),'Professional driver/onboarding object; not a security credential.')
book=rect(79,46,150,150,A,12)+rect(68,36,150,150,S,12,f'stroke="{P}" stroke-width="3"')+path('M99 38v145',P,4)+lines(118,83,76)
put('G11','Trip notebook',group(book,'notebook','book')+star(252,64,21,6,A),'Empty history and planning: an object with blank, clearly illustrative pages.')
docs=group(paper(70,52,124,148)+lines(90,87,75),'back-page','fan-back')+group(paper(115,31,124,148)+lines(139,68,73)+rect(139,130,32,22,A,5),'front-page','fan-front')
put('G12','Document folio',docs,'Application/evidence explanations; submitted/scan states stay in real text.')
people=''
for x,y in [(88,88),(166,62),(236,106)]:people+=group(circle(x,y,20,A)+path(f'M{x-30} {y+68}v-13a30 30 0 0 1 60 0v13Z',P,2,P),f'person-{x}','gather')
put('G13','People together',path('M86 89L166 64 236 107',P,2,extra='stroke-dasharray="5 7"')+people,'Cooperative/onboarding identity; abstract people, not live supply or member counts.')
put('G14','Helpful conversation',group(path('M47 68q0-18 18-18h135q18 0 18 18v75q0 18-18 18h-92l-35 28v-28H65q-18 0-18-18Z',P,3,W)+circle(105,101,7,P)+circle(159,101,7,P)+path('M118 124q15 12 30 0',P,4),'bubble','blink')+group(rect(184,136,79,54,A,18),'small-bubble','float'),'General help art; no new chat, emergency service or response promise.')
calendar=paper(77,40,166,164)+rect(77,40,166,41,P,10)+path('M104 29v28M216 29v28',A,10)
for y in [104,139,174]:
 for x in [105,145,185,221]:calendar+=rect(x-8,y-8,16,16,A if x==145 and y==139 else W,4)
put('G15','Calendar tabs',group(calendar,'calendar','page-turn'),'Scheduling header: actual booking date remains a stable text overlay.')
put('G16','Location compass',circle(160,119,77,W)+circle(160,119,54,'none',f'stroke="{P}" stroke-width="2" stroke-dasharray="3 10"')+group(path('M160 68l22 71-22-13-23 13Z',P,2,P)+circle(160,119,6,A),'pointer','rotate'),'Location rationale illustration; not a changing live GPS heading.')
stops=path('M44 120h232',P,7)
for j,x in enumerate([45,121,199,276]):stops+=circle(x,120,15,S,f'stroke="{P}" stroke-width="4"')+rect(x-16,155,32,6,A,3)
put('G17','Stop rhythm',group(stops,'stops','draw'),'Directional route explainer; real stop labels/order remain data-owned.')
mail=rect(60,106,206,79,P,14)+path('M62 107l59-57h84l59 57',P,3,W)+group(paper(110,53,103,95)+lines(128,80,64),'letter','letter')+path('M65 111l96 51 100-51',A,7)
put('G18','Inbox envelope',mail,'Empty inbox / notification rationale; no imaginary unread arrival.')
lock=path('M118 106V77a42 42 0 0 1 84 0v29',P,10)+rect(97,102,127,98,W,23,f'stroke="{P}" stroke-width="3"')+group(circle(160,141,12,P)+rect(155,146,10,22,P,4),'keyhole','blink')
put('G19','Quiet security',lock,'Security overview/read instructions; authentication outcomes are separate text.')
put('G20','Vehicle blueprint',group(path('M42 71h235M42 67v8M277 67v8M28 119v74M24 119h8M24 193h8',A,2),'dimensions')+car(True),'Vehicle form/detail: a consistent illustration without pretending a photo exists.')
weave=''.join(path(f'M-30 {70+j*28}C80 {0+j*28} 143 {227-j*14} 351 {75+j*28}',P if j%2==0 else A,16) for j in range(4))
put('G21','Road weave',group(weave,'weave','wave'),'Compact administrative header crop; never behind tables/controls.')
dots=''
for yy in range(55,200,14):
 for xx in range(82,245,14):dots+=circle(xx,yy,1.8 if xx<150 else 3,P)
put('G22','Print texture',group(dots,'print','reveal')+circle(215,70,34,A),'Static halftone corner/crop, generated geometry rather than bitmap noise.')
put('G23','Day and night',group(circle(118,105,47,A)+star(118,105,70,12,A),'sun','rotate')+group(path('M214 51a69 69 0 1 0 44 107A61 61 0 0 1 214 51Z',P,2,P),'moon','float'),'Night-driver/account visual; appearance selection stays labelled and controlled.')
spark=path('M117 123l30 31 61-75',P,13)+''.join(star(x,y,r,4,A) for x,y,r in [(75,93,18),(242,142,16),(171,42,12),(137,190,10)])
put('G24','Quiet celebration',group(spark,'spark','spark'),'Finite thank-you accent after a confirmed outcome; pending payments retain pending art.')

def svg(a):return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 240" role="img" aria-label="{a["name"]} original decorative study"><title>{a["name"]}</title>{a["content"]}</svg>'
def main():
 dest=R/'expressive-assets';dest.mkdir(exist_ok=True)
 manifest=[]
 for a in ART.values():
  text=svg(a);f=dest/(a['id']+'.svg');f.write_text(text,encoding='utf8')
  manifest.append({k:v for k,v in a.items() if k!='content'}|{'file':f'expressive-assets/{f.name}','sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'provenance':'Original code-native planning artwork; no third-party image or AI raster input.'})
 (R/'expressive-assets.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 print('24 original vector masters prepared.')
if __name__=='__main__':main()
