# Random notes
## Track Exporter
**Still supported in STK, but never used and actively disabled in export**:
- Checkline: toggling checklines
- Checkline: check-spheres


## General
- Billboards are messed up in Worldblenders 2.8 upgrade
- Blender's particle distribution for objects will crash Worldblenders 2.8 upgrade
- Animation fcurves are treated as if they always use Euler coordinates ordered XYZ (which is Blender's default);
  if an object is animated with quaternions (avoiding gimbal locks) or in any other order of the Euler axes, the export
  will be messed up -> meaning the output in STK will be different than in Blender


Write without fear, and refactor without mercy!
