"""Draw the README system architecture using only Python's standard library.

Run: python3 docs/architecture/render-system.py [output.svg]
Fixed positions keep the three data paths and local/external boundary readable.
"""
from html import escape
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
INK, MUTED, BLUE, AMBER = '#172E42', '#5E7184', '#3468C5', '#A85B15'
parts = ['''<svg xmlns="http://www.w3.org/2000/svg" width="1120" height="1680" viewBox="0 0 1120 1680" role="img" aria-labelledby="title desc">
<title id="title">Clipper system architecture</title>
<desc id="desc">CLI or agents run a local Python pipeline. Video ingestion feeds transcription and a mode router. Clips use AI selection and validation; visual mode uses signal peaks; both are ranked. Re-edits assemble AI-selected lines and bypass ranking. Shared framing, captions and FFmpeg export feed verification and local outputs. Editorial rules, settings, trend briefs and transcript cache support the pipeline. AI-marked modules call the external NYO API.</desc>
<defs>
<marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto-start-reverse"><path d="M1 1L7 4L1 7" fill="none" stroke="#3468C5" stroke-width="1.5"/></marker>
<marker id="aiarrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto-start-reverse"><path d="M1 1L7 4L1 7" fill="none" stroke="#A85B15" stroke-width="1.5"/></marker>
<style>text{font-family:Arial,Helvetica,sans-serif;fill:#172E42}.small{fill:#5E7184}path,line{stroke-linejoin:round;stroke-linecap:round}</style>
</defs><rect width="1120" height="1680" fill="#F7F9FC"/>''']

def rect(x,y,w,h,fill='#FFFFFF',stroke='#CFD9E4',r=12,dash=None):
    parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}"'+(f' stroke-dasharray="{dash}"' if dash else '')+'/>')

def text(x,y,label,size=19,color=INK,bold=False):
    parts.append(f'<text x="{x}" y="{y}" font-size="{size}"'+(' font-weight="700"' if bold else '')+f' style="fill:{color}">{escape(label)}</text>')

def tag(x,y,label='AI'):
    rect(x,y,32,23,'#FFF0DD','#E6C39C',6)
    text(x+7,y+16,label,12,AMBER,True)

def node(x,y,w,h,title,lines=(),ai=False,code=None):
    rect(x,y,w,h,'#FFF9F0' if ai else '#FFFFFF','#E3C49C' if ai else '#CFD9E4')
    text(x+16,y+29,title,20,INK,True)
    if ai:
        tag(x+w-46,y+11)
    for i,label in enumerate(lines):
        text(x+16,y+56+i*25,label,18,MUTED)
    if code:
        text(x+16,y+h-15,code,15,BLUE)

def flow(points,dashed=False,arrow=True):
    path='M'+' L'.join(f'{x} {y}' for x,y in points)
    parts.append(f'<path d="{path}" fill="none" stroke="{AMBER if dashed else BLUE}" stroke-width="2"'+(' stroke-dasharray="5 5"' if dashed else '')+(f' marker-end="url(#{"aiarrow" if dashed else "arrow"})"' if arrow else '')+'/>')

def section(x,y,n,label):
    rect(x,y-17,26,24,INK,INK,6)
    text(x+8,y,n,13,'#FFFFFF',True)
    text(x+38,y,label,15,MUTED,True)

# Header and entry points.
text(40,48,'CLIPPER',16,BLUE,True)
text(40,94,'System architecture',38,INK,True)
text(40,125,'Three processing paths. One local video engine.',21,MUTED)
rect(40,156,1040,112,'#EDF2FA','#D6E0EF',14)
node(60,174,275,76,'YouTube / local video',code='URL or sources/<video>')
node(405,174,300,76,'CLI or coding agent',code='pipeline/clips.py')
node(775,174,285,76,'Campaign configuration',code='settings.local.json')
flow([(335,212),(405,212)])

flow([(918,250),(918,320)],arrow=False)

# Local engine and local supporting files are distinct from the external API.
rect(40,328,770,1120,'#EEF3FA','#B7CADD',18)
text(60,360,'LOCAL ENGINE',17,BLUE,True)
text(485,360,'Python · CPU · FFmpeg',17,MUTED)
section(65,401,'1','INGEST & UNDERSTAND')
flow([(555,250),(555,295),(795,295),(795,412),(172,412),(172,425)])
node(65,425,215,132,'Media loader',['Download / inspect','Decode audio'],code='yt-dlp · ffmpeg')
node(325,425,240,132,'Transcription',['Local speech worker','Words + alignment'],code='transcribe_worker.py')
flow([(280,490),(325,490)])
# Entry connects directly to the media loader without crossing its heading.
node(65,601,720,72,'Mode router',['Speech density + camera cuts; --mode can override'])
flow([(445,557),(445,581),(425,581),(425,601)])
text(460,593,'video + timed words',14,MUTED)

# Supporting files are local, with specific short dependencies.
rect(840,328,240,271,'#F2F4F7','#D2DAE4',14)
text(860,361,'LOCAL RULES',16,MUTED,True)
text(860,399,'Editorial brief',20,INK,True)
text(860,425,'SKILL.md',17,BLUE)
text(860,463,'Trend briefs',20,INK,True)
text(860,489,'trends/*.md',17,BLUE)
text(860,527,'Campaign settings',20,INK,True)
text(860,553,'settings.local.json',17,BLUE)
text(860,582,'trends.py → briefs',16,MUTED)
rect(840,625,240,147,'#F2F4F7','#D2DAE4',14)
text(860,659,'TRANSCRIPT CACHE',16,MUTED,True)
text(860,696,'*.transcript.json',19,INK,True)
text(860,727,'Reuse on the next run',17,MUTED)
text(860,751,'Local · output/<video>/',16,BLUE)
# Cache connector uses the gap between transcription and router.
flow([(565,535),(605,535),(605,575),(825,575),(825,697),(840,697)],arrow=False)
text(660,566,'read / write',14,MUTED)

section(65,716,'2','SELECT A PROCESSING PATH')
for cx in (175,425,675):
    flow([(425,673),(425,731),(cx,731),(cx,754)])
node(65,754,220,122,'Clips',['AI hook selection','Talks / podcasts'],True,'clips.py · pick_hooks()')
node(315,754,220,122,'Visual',['Energy + cut peaks','Gameplay / sports'],False,'pick_by_energy()')
node(565,754,220,122,'Re-edit',['AI line selection','Trailers / promos'],True,'reedit.py · pick_edits()')
node(65,900,220,86,'Validate',['Sentence / length / overlap'])
node(315,900,220,86,'Candidate windows',['Peak-led segments'])
node(565,900,220,86,'Story assembly',['Hook → build → payoff'])
for cx in (175,425,675):
    flow([(cx,876),(cx,900)])
# Continuous modes converge at ranking; the story lane bypasses it.
flow([(175,986),(175,1012),(300,1012),(300,1034)])
flow([(425,986),(425,1012),(300,1012)],arrow=False)
node(65,1034,470,114,'Hook ranking',['Voice + picture + category weights','AI review of 3 phone-cropped frames'],True,'score.py · category() / rank()')
flow([(675,986),(675,1187),(425,1187)],arrow=False)
text(574,1080,'New line order',16,MUTED)
text(574,1105,'Skips ranking',16,MUTED)
flow([(300,1148),(300,1187),(425,1187),(425,1239)])

# Provider boundary uses a single boundary connector plus matching AI badges.
rect(840,824,240,281,'#FFF5E7','#D8B98F',14,'6 5')
text(860,859,'EXTERNAL SERVICE',16,AMBER,True)
text(860,899,'NYO API',26,INK,True)
text(860,930,'glm-5.3-flash',19,AMBER)
text(860,966,'Text + frame requests',17,MUTED)
text(860,996,'AI-tagged modules',17,MUTED)
text(860,1022,'use this endpoint.',17,MUTED)
text(860,1067,'--no-ai: visual only',17,AMBER)
flow([(810,801),(825,801),(825,941),(840,941)],True)
text(850,804,'AI dependency',14,AMBER)
rect(840,1131,240,159,'#F2F4F7','#D2DAE4',14)
text(860,1165,'SHARED INPUTS',16,MUTED,True)
text(860,1200,'Rules → AI selection',17,INK)
text(860,1227,'Settings → run limits',17,INK)
text(860,1254,'Trends → hook brief',17,INK)

section(65,1220,'3','RENDER & VERIFY')
node(65,1239,220,96,'Shot framing',['Crop / split / pad'],code='OpenCV · YuNet')
node(315,1239,220,96,'Timed captions',['Word highlighting'],code='ASS · Montserrat')
node(565,1239,220,96,'Video assembly',['Re-edit cross-fades'],code='FFmpeg · −14 LUFS')
# Render cards are shared component dependencies, not a false sequential flow.
flow([(425,1239),(425,1230),(175,1230),(175,1239)],arrow=False)
flow([(425,1230),(675,1230),(675,1239)],arrow=False)
for cx in (175,425,675):
    flow([(cx,1335),(cx,1355),(425,1355)],arrow=False)
node(245,1372,360,56,'Verify picture / sound / length')
flow([(425,1355),(425,1372)])

# Distinct output contracts.
flow([(425,1428),(425,1475)])
rect(40,1475,1040,142,'#EAF4EE','#ABCAB8',14)
text(60,1505,'LOCAL OUTPUTS',16,'#3D7554',True)
text(60,1540,'Clips / visual',22,INK,True)
text(60,1569,'01-*.mp4 · *.txt · report.md · review.png',18,MUTED)
text(610,1540,'Re-edits → reedit/',22,INK,True)
text(610,1569,'A / B / C shorts · *.txt · report.md',18,MUTED)
text(610,1597,'compare.mp4 when a prior clip exists',16,MUTED)
text(40,1650,'Solid arrows: local data flow     AI badges: NYO dependency     Dashed boundary: external API',16,MUTED)
parts.append('</svg>')
output = Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'system.svg'
output.write_text('\n'.join(parts)+'\n', encoding='utf-8')
print(f'Rendered {output}')
