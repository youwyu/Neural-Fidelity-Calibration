# NFC interactive teaser

The teaser keeps a **720 × 720 snowy Jackal video on the left** and **eight
simulation views in a 2 × 4 grid on the right**. The right-hand preview button,
**real-to-sim via NFC**, activates the interactive views without hiding the left
video. The small orbit/zoom and terrain-size captions have been removed.
The six experiment videos remain separate.

## Scene and interaction

- Eight simultaneously visible **12.8 m × 12.8 m** MuJoCo domain samples, each with eight
  independently moving, original-scale open-frame Jackals (64 distinct routes).
- Drag to orbit, scroll or pinch to zoom, and right-drag or arrow keys to pan.
  Each tile orbits independently; the shared controls restore robot following
  or frame all eight full terrains. Motion can be paused, and the
  snow-reference grid can be hidden.
- Gray matte chassis and wheels with the entire front-left tire colored in one
  of eight pink-to-burgundy shades. Wheel centers, 9.5 cm radius, and 4 cm width
  match the original Jackal URDF. Robot geometry is never enlarged.
- A dashed, world-fixed grid covers the entire observed snow surface with 25 cm
  line spacing. The solid terrain underneath is a sampled support surface. The
  Δh label gives the sampled snow depth at the selected robot.
- Every robot follows a distinct figure-eight with its own phase, rotation,
  amplitudes, direction, lap count, and speed modulation. All routes loop over
  32 simulation seconds, played at 2× speed.

These are **handcrafted illustrative posterior samples**, with prescribed chassis
poses and rolling wheels. No NFC inference, policy, or physics engine runs in
the browser. They do not validate actuator losses or autonomous adaptation.
Red intensity represents an impairment hypothesis, not measured wheel torque.

## Lightweight loading

The small loader, two JPEG previews (about 211 KB combined), and markup load
initially. The left video is about 902 KB, with `preload="none"`.
The renderer, Three.js r180, and compact route parameters are bundled into one
classic script, fetched only after a click. It works with direct `file://` HTML
previews as well as HTTP hosting, without module imports or JSON fetches at
runtime. The optional bundle is under 0.8 MB (about 0.2 MB with gzip).
Three.js is vendored with its MIT license in `static/js/vendor/three/LICENSE`;
there are no runtime CDN dependencies.

Eight scenes share one canvas using scissored viewports, capped at 24 fps and
device pixel ratio 1.25. Shared chassis geometry and instanced wheels keep each
environment to two robot draw calls. Shadow maps are capped at 512 pixels. Rendering stops offscreen, when closed, and in background tabs.
A paused view renders only after camera or scene changes. Reduced motion starts
the robots paused. Opening 3D pauses experiment videos and starts the left video alongside the
robots (unless reduced motion is enabled). Play/pause controls operate on both.
Playing an experiment pauses the robots and left video. The experiment clips use 720p/30 fps, `preload="none"`, posters,
and native controls, with no autoplay or looping.

## Scene sources

`scene_common.py` contains the shared snow-height function, support-plane fit,
and original Jackal visual reader. The detailed preview model comes from
`/media/soicroot/IU9/code/SimRealOffroad/assets/jackal`; that directory is read-only.
The left preview shows an uneven snow field rendered with Chrono SCM and
Sensor/OptiX. Its tires remain black. The right preview uses MuJoCo, neutral
materials, and six dim lights for softer overlapping shadows. Main tracking
close-ups are retained; no miniature terrain insets are present.

`render_domains.py` and `render_chrono.py` retain the offline source scenes and
write provenance manifests. `compose_teaser.py` is an offline helper to combine
rendered frames into temporary media for the preview; its video output is not
served by the website. Local intermediate assets are kept under `/tmp`.

After modifying the domain manifest, export the compact web data with:

```bash
python design/teaser/export_web_samples.py
# Node.js 18+; build tooling is not shipped to visitors.
npx --yes esbuild@0.25.10 static/js/teaser-viewer.js --bundle --format=iife \
  --global-name=NFCTeaserViewer --target=es2020 --minify --legal-comments=linked \
  --outfile=static/js/teaser-viewer.bundle.js
```

Rebuild the bundle after editing the viewer, motion code, or sample data.

The browser motion lives in `static/js/teaser-motion.mjs`. Its support-plane fit
and route equations match the offline renderer: 1,024 sampled poses across all
64 routes agreed to floating-point precision in local validation.

To refresh the static preview from offline detail renders:

```bash
python design/teaser/compose_teaser.py --detail /tmp/nfc-full-grid-final \
  --output /tmp/nfc-preview-source
ffmpeg -y -ss 3.5 -i /tmp/nfc-full-grid-final/chrono-snow.mp4 \
  -vf scale=720:720 -frames:v 1 -q:v 2 static/images/teaser-snow.jpg
ffmpeg -y -ss 3.5 -i /tmp/nfc-full-grid-final/domains.mp4 \
  -vf scale=1440:720 -frames:v 1 -q:v 2 static/images/teaser-simulations.jpg
```

No changes have been published.

References:
- https://github.com/RobotiXX/verti_bench
- https://generalist-locomotion.github.io/
- https://php-parkour.github.io/demo.html
