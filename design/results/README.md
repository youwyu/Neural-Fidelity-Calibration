# Paper posterior results

`posterior_figure.tex` is the exact fragment supplied on September 9, 2026. Its
80 vector-traced density panels, 5,760 sample points, truth crosses, posterior
means, method labels, and palette are preserved.

The website displays all five robot rows together, above the experiment videos.
Flat and Rough tabs switch the method columns. The Rough view includes residual
dynamics and residual environment as its two rightmost columns. Hovering over
a plotted sample reveals its normalized coordinates; clicking pins the selection.
Arrow keys inspect samples, and the enlarge button or Enter opens a comparison
with interactive samples and ground-truth/posterior-mean coordinates. Calibration
comparisons show flat and rough panels together; residual comparisons show two
parameter slices. No probability values or unprovided metrics are inferred.

All 80 panels are rendered directly from the original TikZ paths and points as
512-pixel WebP assets, about 1.15 MB combined. The source panel translation is
removed only to put each panel on its own page. Images load lazily, and sample
metadata loads near the results section as a classic script, supporting direct
`file://` previews. Each plot uses one SVG highlight circle; there are no charting
libraries, animation loops, canvas renderers, or runtime posterior computations.
The full static figure has been removed from the page. Its archival exports and
build source remain available in the repository.

Robot labels use generic quadruped and aerial-robot names because the archived
system names and replacement snapshot model names differ. The five snapshots
used in the archival full figure came from
`/home/soicroot/Youwei/research/CoRL24/Adaptive-Diffusion-Terrain/figures/posterior_tikz/assets/`.
Copies here are reduced to at most 500 pixels on either side; originals are unchanged.
The table uses these paper snapshots instead of visible robot labels, retaining
accessible image descriptions. Its lazy-loaded 240-pixel WebP copies in
`static/images/results-robots/` total about 41 KB.

Rebuild interactive assets with TeX Live (standalone, TikZ, graphicx), Poppler,
and Pillow:

```bash
python design/results/build_panels.py
```

To regenerate the archival full-figure exports separately:

```bash
python design/results/build_results.py
```

Intermediate PDFs stay in temporary directories.
