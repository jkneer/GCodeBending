# GCodeBending
 This is a quick and dirty Python code to deform GCode so that it follows a defined spline.
# Requirements
- GCode needs to be sliced with relative extrusions activated, preferably in PrusaSlicer
- You need enough clearance around your nozzle to print significant angles
- The model can't be too large in the X dimension, otherwise you'll get self intersections
# Usage
- Place your part preferably in the middle of your print plate with known center X coordinates
- Place the sliced GCode in the same directory as the Python script
- Set the options either in config.json and run the script with *python bend_gcode.py --json-config=config.json*
- Or, set the options that you require by command line: *python bend_gcode.py -i myinputfile.gcode ...*
- Use *python bend_gcode.py --help* to learn about the available options.