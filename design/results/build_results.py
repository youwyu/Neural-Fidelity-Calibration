"""Render the supplied paper fragment as static, lightweight website images."""
from pathlib import Path
import shutil
import subprocess
import tempfile
from PIL import Image

source = Path(__file__).resolve().parent
root = source.parents[1]
with tempfile.TemporaryDirectory(prefix='nfc-results-') as directory:
    work = Path(directory)
    for filename in ('posterior.tex', 'posterior_figure.tex'):
        shutil.copy2(source/filename, work/filename)
    shutil.copytree(source/'assets', work/'assets')
    subprocess.run(['pdflatex', '-no-shell-escape', '-interaction=nonstopmode',
                    '-halt-on-error', 'posterior.tex'], cwd=work, check=True,
                   stdout=subprocess.DEVNULL)
    for width, name in ((2800, 'preview'), (4200, 'full')):
        subprocess.run(['pdftoppm', '-scale-to', str(width), '-singlefile', '-png',
                        str(work/'posterior.pdf'), str(work/name)], check=True)
    preview = Image.open(work/'preview.png').convert('RGB')
    preview.save(root/'static/images/posterior.webp', quality=90, method=6)
    Image.open(work/'full.png').save(root/'static/images/posterior.png', optimize=True)
    print('Preview dimensions:', preview.size)
