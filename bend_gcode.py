# -*- coding: utf-8 -*-
"""
Created on Wed Jan 12 10:10:14 2022

@author: stefa
@author: jkneer
"""

import re
from collections import namedtuple

import numpy as np
from scipy.interpolate import CubicSpline, PPoly

import pydantic_cli
from gcodebending import BendingConfig

Point2D = namedtuple('Point2D', 'x y')
GCodeLine = namedtuple('GCodeLine', 'x y z e f')


def plot_spline(X: tuple, Z: tuple, spline: PPoly) -> None:
    """Plot the spline"""
    import matplotlib.pyplot as plt
    xs = np.arange(0, Z[-1],1)
    _, ax = plt.subplots(figsize=(6.5, 4))
    ax.plot(X, Z, 'o', label='data')
    ax.plot(spline(xs), xs, label="S")
    ax.set_xlim(0, 200)
    ax.set_ylim(0, 200)
    plt.gca().set_aspect('equal', adjustable='box')
    # ax.legend(loc='lower left', ncol=2)
    plt.show()


def get_normalpoint(currentPoint: Point2D, derivative: float, distance: float) -> Point2D:
    """claculates the normal of a point on the spline"""
    angle = np.arctan(derivative) + np.pi /2
    return Point2D(currentPoint.x + distance * np.cos(angle), currentPoint.y + distance * np.sin(angle))

def parse_gcode_line(currentLine: str) -> GCodeLine:
    """parse a G-Code line"""
    thisLine = re.compile('(?i)^[gG][0-3](?:\s+x(?P<x>-?[0-9.]{1,15})|\s+y(?P<y>-?[0-9.]{1,15})|\s+z(?P<z>-?[0-9.]{1,15})|\s+e(?P<e>-?[0-9.]{1,15})|\s+f(?P<f>-?[0-9.]{1,15}))*')
    lineEntries = thisLine.match(currentLine)
    if lineEntries:
        return GCodeLine(lineEntries.group('x'), lineEntries.group('y'), lineEntries.group('z'), lineEntries.group('e'), lineEntries.group('f'))

def write_line(outputFile, G, X, Y, Z, F = None, E = None):
    """write a line to the output file"""
    outputSting = "G" + str(int(G)) + " X" + str(round(X,5)) + " Y" + str(round(Y,5)) + " Z" + str(round(Z,3))
    if E is not None:
        outputSting = outputSting + " E" + str(round(float(E),5))
    if F is not None:
        outputSting = outputSting + " F" + str(int(float(F)))
    outputFile.write(outputSting + "\n")

# about ~x30 faster than original
def on_spline_length(z:float, x_lookup: np.ndarray, disc_length: float) -> float:
    """Calcuate corrected height"""
    res = np.where(x_lookup>=z)
    try:
        index = res[0][0]
    except IndexError:
        raise IndexError('Spline not defined high enough')
    return index*disc_length

def create_x_lookuptable(Z: tuple, disc_length: float, dx_spline: PPoly) -> np.ndarray:
    """Create a lookup table for sum(dx)"""
    height = np.arange(Z[0], Z[-1], disc_length)
    dx = dx_spline(height)
    tx = np.cumsum( np.sqrt((dx[1:]-dx[:-1])**2 + disc_length**2) )
    x = np.insert(tx, 0, 0.0)
    return x



def main(cfg: BendingConfig):
    # cfg = BendingConfig()

    dx_spline = CubicSpline(cfg.spline_z, cfg.spline_x, bc_type=((1, 0), (1, cfg.bending_angle)))
    
    if cfg.debug:
        plot_spline(cfg.spline_x, cfg.spline_z, dx_spline)
    
    lastPosition = Point2D(0, 0)
    currentZ = 0.0
    lastZ = 0.0
    currentLayer = 0
    relativeMode = False
    SplineLookupTable = create_x_lookuptable(cfg.spline_z, cfg.discretization_length, dx_spline)
    
    
    # TODO: this is the prototype of structure to be refactured to the new
    #       match-statement of python 3.10
    with open(cfg.input, "r") as gcodeFile, open(cfg.output, "w+") as outputFile:
            for currentLine in gcodeFile:
                if currentLine[0] == ";":   #if NOT a comment
                    outputFile.write(currentLine)
                    continue
                if currentLine.find("G91 ") != -1:   #filter relative commands
                    relativeMode = True
                    outputFile.write(currentLine)
                    continue
                if currentLine.find("G90 ") != -1:   #set absolute mode
                    relativeMode = False
                    outputFile.write(currentLine)
                    continue
                if relativeMode: #if in relative mode don't do anything
                    outputFile.write(currentLine)
                    continue
                currentLineCommands = parse_gcode_line(currentLine)
                if currentLineCommands is not None: #if current comannd is a valid gcode
                    if currentLineCommands.z is not None: #if there is a z height in the command
                        currentZ = float(currentLineCommands.z)
                        
                    if currentLineCommands.x is None or currentLineCommands.y is None: #if command does not contain x and y movement it#s probably not a print move
                        if currentLineCommands.z is not None: #if there is only z movement (e.g. z-hop)
                            outputFile.write("G91\nG1 Z" + str(currentZ-lastZ))
                            if currentLineCommands.f is not None:
                                outputFile.write(" F" + str(currentLineCommands.f))
                            outputFile.write("\nG90\n")
                            lastZ = currentZ
                            continue
                        outputFile.write(currentLine)
                        continue
                    currentPosition = Point2D(float(currentLineCommands.x), float(currentLineCommands.y))
                    midpointX = lastPosition.x + (currentPosition.x - lastPosition.x) / 2  #look for midpoint
                    
                    distToSpline = midpointX - cfg.spline_x[0]
                    
                    #Correct the z-height if the spline gets followed
                    #correctedZHeight = onSplineLength(currentZ)
                    correctedZHeight = on_spline_length(currentZ, SplineLookupTable, cfg.discretization_length)
                                    
                    angleSplineThisLayer = np.arctan(dx_spline(correctedZHeight, 1)) #inclination angle this layer
                    
                    angleLastLayer = np.arctan(dx_spline(correctedZHeight - cfg.layer_height, 1)) # inclination angle previous layer
                    
                    heightDifference = np.sin(angleSplineThisLayer - angleLastLayer) * distToSpline * -1 # layer height difference
                    
                    transformedGCode = get_normalpoint(Point2D(correctedZHeight, dx_spline(correctedZHeight)), dx_spline(correctedZHeight, 1), currentPosition.x - cfg.spline_x[0])
                    
                    #Check if a move is below Z = 0
                    if float(transformedGCode.x) <= 0.0: 
                        print("Warning! Movement below build platform. Check your spline!")
                    
                    #Detect unplausible moves
                    if transformedGCode.x < 0 or np.abs(transformedGCode.x - currentZ) > 50:
                        print("Warning! Possibly unplausible move detected on height " + str(currentZ) + " mm!")
                        outputFile.write(currentLine)
                        continue    
                    #Check for self intersection
                    if (cfg.layer_height + heightDifference) < 0:
                        print("ERROR! Self intersection on height " + str(currentZ) + " mm! Check your spline!")
                        
                    #Check the angle of the printed layer and warn if it's above the machine limit
                    if angleSplineThisLayer > (cfg.warning_angle * np.pi / 180.):
                        print("Warning! Spline angle is", (angleSplineThisLayer * 180. / np.pi), "at height  ", str(currentZ), " mm! Check your spline!")
                                                        
                    if currentLineCommands.e is not None: #if this is a line with extrusion
                        """if float(currentLineCommands.e) < 0.0:
                            print("Retraction")"""
                        extrusionAmount = float(currentLineCommands.e) * ((cfg.layer_height + heightDifference)/cfg.layer_height)
                        #outputFile.write(";was" + currentLineCommands.e + " is" + str(extrusionAmount) + " diff" + str(int(((LAYER_HEIGHT + heightDifference)/LAYER_HEIGHT)*100)) + "\n")
                    else:
                        extrusionAmount = None                    
                    write_line(outputFile, 1,transformedGCode.y, currentPosition.y, transformedGCode.x, None, extrusionAmount)
                    lastPosition = currentPosition
                    lastZ = currentZ
                else:
                    outputFile.write(currentLine)
    print("GCode bending finished!")


if __name__ == '__main__':
    pydantic_cli.run_and_exit(BendingConfig, main, 'Bend GCode')
