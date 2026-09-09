"""Export routes and sample parameters without large per-frame histories."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
manifest = json.loads((root/'design/teaser/domains-manifest.json').read_text())
config = dict(terrain_size_m=manifest['terrain_size_m'], period=32, samples=[dict(
    depth_parameter_m=sample['depth_parameter_m'],
    robots=[{key: value for key, value in robot.items() if key != 'frames'}
            for robot in sample['robots']]) for sample in manifest['samples']])
(root/'static/data/teaser-domains.json').write_text(json.dumps(config, separators=(',', ':')))
