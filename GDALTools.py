# authors:
# David Hernandez Lopez, david.hernandez@uclm.es

import os, sys
from osgeo import gdal, osr, ogr


current_path = os.path.dirname(__file__)
sys.path.append(os.path.join(current_path, '..'))

from . import defs_gdal
from pyLibCRSs import CRSsDefines as defs_crs
from pyLibCRSs.CRSsTools import CRSsTools

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

class GDALTools(object):
    is_initialized = False
    crs_tools = None
    driver_names_by_file_extension = {}
    vector_drivers_file_extensions = []
    raster_drivers_file_extensions = []

    @classmethod
    def get_driver_name_from_file(self, file_path):
        str_error = ''
        driver_name = ''
        if not isinstance(file_path, str):
            str_error = ('File path must be a string and is a: {}'.format(str(type(file_path))))
            return str_error, driver_name
        if not self.is_initialized:
            str_error = self.initialize()
            if str_error:
                return str_error, driver_name
        file_extension_without_dot = os.path.splitext(file_path)[1][1:]
        if not file_extension_without_dot in self.driver_name_by_file_extension:
            str_error = ('Not found driver for file extension: {}'.format(file_extension_without_dot))
            return str_error, driver_name
        driver_name = self.driver_name_by_file_extension[file_extension_without_dot]
        return str_error, driver_name

    @classmethod
    def initialize(self):
        str_error = ''
        self.crs_tools = CRSsTools()
        raster_drivers = []
        vector_drivers = []
        for i in range(gdal.GetDriverCount()):
            drv = gdal.GetDriver(i)
            md = drv.GetMetadata_Dict()
            driver_name = str(drv.ShortName)
            driver_extensions = drv.GetMetadataItem(gdal.DMD_EXTENSIONS)
            if not driver_extensions:
                continue
            driver_extensions = driver_extensions.split()
            # if isinstance(driver_extensions, str):
            #     driver_extensions = [driver_extensions]
            for j in range(len(driver_extensions)):
                driver_extension = driver_extensions[j]
                if not driver_extension in self.driver_names_by_file_extension:
                    self.driver_names_by_file_extension[driver_extension] = []
                if not driver_name in self.driver_names_by_file_extension[driver_extension]:
                    self.driver_names_by_file_extension[driver_extension].append(driver_name)
                if defs_gdal.GDAL_TAG_RASTER in md:
                    if not driver_extension in self.raster_drivers_file_extensions:
                        self.raster_drivers_file_extensions.append(driver_extension)
                if defs_gdal.GDAL_TAG_VECTOR in md:  # note some drivers can handle both raster and vector
                    if not driver_extension in self.vector_drivers_file_extensions:
                        self.vector_drivers_file_extensions.append(driver_extension)
        return str_error

