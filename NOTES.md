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
- There is a minor bug that affects exported checklines: only the left edge of the line is considered for the height
  testing of the driveline
- The 'sfx-emitter' and 'action-trigger' object type in the scene.xml file must be processed after the check structures
  (XML node placed after checks) otherwise lap counting will be messed up. It seems it has something to do with conditional scripting functions that interfere with checkline action triggers.


Write without fear, and refactor without mercy!
