import pathlib
import pydantic
import pydantic_cli
import json

import numpy as np

from typing import Any


# def json_config_settings_source(settings: pydantic.BaseSettings) -> dict[str, Any]:
#     """
#     A simple settings source that loads variables from a JSON file
#     at the project's root.

#     Here we happen to choose to use the `env_file_encoding` from Config
#     when reading `config.json`
#     """
#     encoding = settings.__config__.env_file_encoding
#     return json.loads(pathlib.Path('config.json').read_text(encoding))

class BendingConfig(pydantic.BaseSettings):
    input: str = pydantic.Field('input.gcode', description='Input gcode file', cli=('-i', '--input-file'))
    output: str = pydantic.Field('output.gcode', description='Output gcode file', cli=('-o', '--output-file'))
    
    layer_height: float = pydantic.Field(0.3, description="Layer height of the input gcode file. Important, because you don't set it correctly you'll get under- or over extrusions", cli=('-l', '--layer-height'))
    warning_angle: float = pydantic.Field(30.0, description='Maximum printable angle your system can print at due to clearances.', cli=('-a','--warning-angle'))
    
    spline_x: tuple[float, ...] = pydantic.Field((125.0, 95.0), description='Array that can contain any number of points > 2. Make sure the first X-coordinate is in the center of your part. Make sure the last z coordinate is higher or equal the highest z-coordiante in your GCode.', cli=('-sx', '--spline-x'))
    spline_z: tuple[float, ...] = pydantic.Field((0.0, 140.0), description='Same as spline-x. Additionally,  of points > 2. Additionally, make sure the last z coordinate is higher or equal the highest z-coordiante in your GCode.', cli=('-sz', '--spline-z'))
    bending_angle: float = pydantic.Field(-np.pi/6, description='This defines the final angle of the spline in rad.', cli=('-b', '--bending-angle'))
    
    discretization_length: float = pydantic.Field(0.01, description='Discretization in z', cli=('-dz', '--discretization-length'))
    
    debug: bool = pydantic.Field(False, description='Enable debugging mode', cli=('-d', '--enable-debug'))
    
    @pydantic.root_validator(pre=False)
    @classmethod
    def check_splineconsistency(cls, values):
        """Ensure there is the same number of coordinates in spline_XXX
        and they have a minimum length of 2"""
        if len(values['spline_x']) != len(values['spline_z']):
            raise ValueError('Spline parameters need to have same length.')
        return values
        
    @pydantic.validator('spline_x', 'spline_z')
    @classmethod
    def check_splinemin(cls, value):
        if len(value) < 2:
            raise ValueError('Spline needs at least 2 points')
        return value
    
    
    class Config(pydantic_cli.DefaultConfig):
        CLI_JSON_ENABLE = True
        env_file_encoding = 'utf-8'
        CLI_BOOL_PREFIX = ('--enable-', '--disable-')
        

        # @classmethod
        # def customise_sources(
        #     cls,
        #     init_settings,
        #     env_settings,
        #     file_secret_settings,
        # ):
        #     return (
        #         init_settings,
        #         json_config_settings_source,
        #         env_settings,
        #         file_secret_settings,
        #     )
    
