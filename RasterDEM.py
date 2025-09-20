# authors:
# David Hernandez Lopez, david.hernandez@uclm.es

import os, sys
from osgeo import gdal, osr, ogr
import json
import numpy as np
# import numpy.ma as ma
import psutil
import math
from statistics import mode

import subprocess

current_path = os.path.dirname(__file__)
sys.path.append(os.path.join(current_path, '..'))

from . import defs_gdal
from pyLibCRSs import CRSsDefines as defs_crs
from pyLibCRSs.CRSsTools import CRSsTools
from .GDALTools import GDALTools
from .Raster import Raster

gdal.UseExceptions()


class GdalErrorHandler(object):
    def __init__(self):
        self.err_level = gdal.CE_None
        self.err_no = 0
        self.err_msg = ''

    def handler(self, err_level, err_no, err_msg):
        self.err_level = err_level
        self.err_no = err_no
        self.err_msg = err_msg

err = GdalErrorHandler()
gdal.PushErrorHandler(err.handler)
gdal.UseExceptions()  # Exceptions will get raised on anything >= gdal.CE_Failure
assert err.err_level == gdal.CE_None, 'the error level starts at 0'

class RasterDEM(Raster):
    def __init__(self,
                 precision = 3):
        # precision -1 for no try to optimize data type
        # precision 0 for round as integer float values
        super().__init__(precision)
