# Visual references and composition decisions

Inspected for presentation ideas; no external figure imagery is included in the
website or teaser assets.

- **Cully et al., Nature (2015), “Robots that can adapt like animals,” Figure 1.**
  https://www.nature.com/articles/nature14422
  Hardware close-ups make the robot readable; a targeted red annotation identifies
  the damaged part. The lower panels use simplified simulation geometry and
  trajectories rather than equally emphasizing every detail of the scene.
- **Miki et al., Science Robotics (2022), “Learning robust perceptive locomotion
  for quadrupedal robots in the wild,” Figures 1, 3 and 4.**
  https://doi.org/10.1126/scirobotics.abk2822
  Author manuscript: https://arxiv.org/abs/2201.08117
  Figure 1 shows robots at useful scales within their environments. Figure 3 pairs
  real views with terrain reconstructions and a magnified contact-region inset.
  Figure 4 makes the robot and local terrain estimates large enough to compare.

- **LocoFormer, “Generalist Locomotion via Long-Context Adaptation” (CoRL 2025).**
  https://generalist-locomotion.github.io/
  The user's supplied screenshot guides the matte materials, neutral gray ground,
  readable simplified robot geometry, and soft lighting. The right-side renders
  use lighter gray chassis with red reserved for the front-left tire.

## Current presentation

The displayed teaser keeps the large tracking close-ups and removes the small
full-terrain insets. The 2 × 4 environment layout, all 64 independent simulation
trajectories, 12.8 m square terrains, and original robot scale are retained.

The dashed snow reference now covers the complete terrain and stays fixed in
world coordinates. Six dim directional lights soften the robot shadows; the
terrain and unhighlighted robot parts use a restrained gray palette.

The final website uses an on-demand 3D sample explorer inspired by the camera
interaction at https://php-parkour.github.io/demo.html. It runs prescribed motion
and allows orbit, pan, zoom, and robot following. A static comparison preview
loads initially; the teaser video and its switching controls have been removed.

The current layout retains the snowy Jackal video on the left. The right-hand
button, “real-to-sim via NFC,” replaces only the simulation preview with eight
independently orbitable terrains, rendered through a single canvas.
