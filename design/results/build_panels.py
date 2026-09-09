"""Export the paper's exact TikZ panels and marker coordinates for interaction."""
from pathlib import Path
import json
import re
import subprocess
import tempfile
from PIL import Image

source = Path(__file__).resolve().parent
root = source.parents[1]
text = (source/'posterior_figure.tex').read_text()
blocks = re.findall(r'% Exact vector trace: ([^;]+); embedded image (\d+)\n(.*?\\end\{scope\})', text, re.S)
assert len(blocks) == 80, f'Expected 80 panels, got {len(blocks)}'
robot_ids = ['Ant', 'Anymal', 'Humanoid', 'Quadcopter', 'Jackal']
robot_labels = ['Ant', 'Quadruped', 'Humanoid', 'Aerial robot', 'Jackal']
pages, panels = [], []
for number, (title, image_id, block) in enumerate(blocks, 1):
    robot, environment, method = title.split(' ', 2)
    assert environment in ('flat', 'rough', 'residual')
    # Translate each original panel to its own page; retain every path and point.
    local = re.sub(r'\\begin\{scope\}\[[^\n]+\]', r'\\begin{scope}', block, count=1)
    pages.append('\\begin{tikzpicture}[x=1cm,y=1cm]\n'+local+
                 '\n\\pgfresetboundingbox\\path[use as bounding box] (0,0) rectangle (1,1);\n\\end{tikzpicture}')
    def center(color):
        line = next(line for line in block.splitlines() if '\\draw['+color+',' in line)
        points = re.findall(r'\((-?[\d.]+),(-?[\d.]+)\)', line)
        return [round((float(points[0][axis])+float(points[1][axis]))/2, 5) for axis in (0, 1)]
    sample_line = next(line for line in block.splitlines() if r'\foreach \SX/\SY in' in line)
    samples = [[float(x), float(y)] for x, y in re.findall(r'(-?[\d.]+)/(-?[\d.]+)', sample_line)]
    assert samples, title
    panels.append(dict(samples=samples, robot=robot_ids.index(robot), environment=environment,
                       method=method, mean=center('CompCenter'), truth=center('Truth'),
                       source_image=int(image_id), file=f'panel-{number:02}.webp'))
with tempfile.TemporaryDirectory(prefix='nfc-posterior-panels-') as directory:
    work = Path(directory)
    definitions = text[text.index('\\begingroup'):text.index('\\noindent')]
    (work/'panels.tex').write_text('\\documentclass[tikz,multi=true,border=0pt]{standalone}\n'
        '\\usepackage{graphicx}\n\\begin{document}\n'+definitions+'\n'.join(pages)+
        '\n\\endgroup\n\\end{document}\n')
    subprocess.run(['pdflatex', '-no-shell-escape', '-interaction=nonstopmode',
                    '-halt-on-error', 'panels.tex'], cwd=work, check=True, stdout=subprocess.DEVNULL)
    info = subprocess.check_output(['pdfinfo', str(work/'panels.pdf')], text=True)
    assert re.search(r'Pages:\s+80\b', info)
    subprocess.run(['pdftoppm', '-scale-to', '512', '-png', str(work/'panels.pdf'),
                    str(work/'panel')], check=True)
    output = root/'static/images/results-panels'
    output.mkdir(exist_ok=True)
    for number, panel in enumerate(panels, 1):
        Image.open(work/f'panel-{number:02}.png').convert('RGB').save(
            output/panel['file'], quality=92, method=6)
config = dict(robots=robot_labels, panels=panels)
(root/'static/js/results-data.js').write_text(
    '// Extracted from the supplied paper figure; coordinates are normalized.\n'
    'window.NFCResultsData='+json.dumps(config, separators=(',', ':'))+';\n')
print('Exported all 80 panels with source-derived ground truth and posterior means.')
