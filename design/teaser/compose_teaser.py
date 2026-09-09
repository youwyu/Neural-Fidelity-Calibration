"""Compose the main robot views without overview insets."""
import argparse
import json
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--detail', type=Path, default=Path('/tmp/nfc-detail'))
parser.add_argument('--overview', type=Path, default=Path('/tmp/nfc-overview'))
parser.add_argument('--output', type=Path, default=Path('/tmp/nfc-composed'))
parser.add_argument('--view', choices=['detail', 'overview'], default='detail')
a = parser.parse_args()
a.output.mkdir(parents=True, exist_ok=True)
source_dir = a.detail if a.view == 'detail' else a.overview
sources = [source_dir/'chrono-snow.mp4', source_dir/'domains.mp4']
filters = '[0:v][1:v]hstack=inputs=2'
if a.view == 'detail':
    # Thin panel boundaries retain the 2x4 layout; no miniature views are overlaid.
    for row in range(2):
        for col in range(4):
            filters += f',drawbox=x={1080+col*540}:y={row*540}:w=540:h=540:color=0xf8f8f8:t=2'
filters += ',scale=2160:720:flags=lanczos[v]'
subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
                '-i', str(sources[0]), '-i', str(sources[1]),
                '-filter_complex', filters, '-map', '[v]', '-an',
                '-c:v', 'libx264', '-crf', '24', '-preset', 'slow',
                '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(a.output/'teaser.mp4')], check=True)
(a.output/'composition.json').write_text(json.dumps(dict(
    presentation=f'{a.view} views without insets', insets=False,
    size=[2160,720], fps=24, frames=384, terrain_size_m=[12.8,12.8],
    robot_scale=1.0, source_paths=[str(path) for path in sources]), indent=2))
print('FINISHED', flush=True)
