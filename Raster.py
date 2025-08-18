# authors:
# David Hernandez Lopez, david.hernandez@uclm.es

import os, sys
from osgeo import gdal, osr, ogr
import json
from numpy import *

import subprocess

current_path = os.path.dirname(__file__)
sys.path.append(os.path.join(current_path, '..'))

from . import defs_gdal
from pyLibCRSs import CRSsDefines as defs_crs
from pyLibCRSs.CRSsTools import CRSsTools
from .GDALTools import GDALTools

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

class Raster:
    def __init__(self,
                 precision = 3):
        self.crs_tools = CRSsTools()
        self.data_set = None
        self.precision = precision
        self.dbl_to_int = 10. ** precision
        self.int_to_dbl = 1.0 / self.dbl_to_int
        self.crs = None
        self.crs_epsg_code = None
        self.crs_id = None
        self.georef = None
        self.rows = None
        self.columns = None
        self.size_fc = None
        self.size_sc = None
        self.grid_size = None
        self.number_of_bands = None
        self.nw_fc = None
        self.nw_sc = None
        self.ne_fc = None
        self.ne_sc = None
        self.se_fc = None
        self.se_sc = None
        self.sw_fc = None
        self.sw_sc = None
        self.scale_by_band = {}
        self.offset_by_band = {}
        self.min_value_by_band = {}
        self.max_value_by_band = {}
        self.raster_by_band = {}
        self.gdal_data_type_by_band = {}
        self.no_data_value_by_band = {}
        self.data_by_band = {}
        self.file_path = None

    def set_from_file(self,
                      file_path,
                      load_data = False):
        str_error = ''
        if not isinstance(file_path, str):
            str_error = ('File path must be a string and is a: {}'.format(str(type(file_path))))
            return str_error
        str_error, is_raster = GDALTools.is_raster(file_path)
        if str_error:
            return str_error
        if not is_raster:
            str_error = ('File:\n{}\nis not a raster'.format(file_path))
        self.data_set = None
        try:
            self.data_set = gdal.Open(file_path)
        except Exception as e:
            str_error = 'GDAL Error: ' + e.args[0]
        if not self.data_set:
            str_error = ('File is not a valid raster data source:\n{}'.format(file_path))
            return str_error
        self.columns = self.data_set.RasterXSize
        self.rows = self.data_set.RasterYSize
        self.crs = None
        self.crs_epsg_code = None
        self.crs_id = None
        self.crs = self.data_set.GetSpatialRef()
        srs_unit = ""
        if self.crs: # compound is pending
            srs_as_projjson = json.loads(self.crs.ExportToPROJJSON())
            srs_as_wkt = self.crs.ExportToPrettyWkt()
            is_compound = self.crs.IsCompound()
            if is_compound:
                str_error, epsg_code, vertical_epsg_code = self.crs_tools.get_compound_epgs_codes_from_json(srs_as_projjson)
                if str_error:
                    return str_error
            # print("SRS:")
            # srs_type = srs_as_projjson["type"]
            # print(f"  Type: {srs_type}")
            # name = srs_as_projjson["name"]
            # print(f"  Name: {name}")
            if "id" in srs_as_projjson:
                id = srs_as_projjson["id"]
                authority = id["authority"]
                code = id["code"]
                if authority.casefold() == 'EPSG'.casefold():
                    self.crs_id = ("{}:{}".format(authority, str(code)))
                    self.crs_epsg_code = code
                # print(f"  Id: {authority}:{code}")
            # srs_unit = " " + srs_as_projjson["coordinate_system"]["axis"][0]["unit"]
        self.geotransform = self.data_set.GetGeoTransform()
        self.size_fc = self.geotransform[1]
        self.size_sc = self.geotransform[5]
        self.grid_size = abs(self.size_fc)
        if (abs(self.size_sc) > self.grid_size):
            self.grid_size = abs(self.size_sc)
        if self.geotransform[2] == 0 and self.geotransform[4] == 0:
            self.nw_fc = self.geotransform[0]
            self.nw_sc = self.geotransform[3]
        else:
            self.nw_fc = self.geotransform[0] - 0.5 * self.geotransform[1] - 0.5 * self.geotransform[2]
            self.nw_sc = self.geotransform[3] - 0.5 * self.geotransform[4] - 0.5 * self.geotransform[5]
        self.ne_fc = self.geotransform[0] + self.columns * self.geotransform[1] + 0.0 * self.geotransform[2]
        self.ne_sc = self.geotransform[3] + self.columns * self.geotransform[4] + 0.0 * self.geotransform[5]
        self.se_fc = self.geotransform[0] + self.columns * self.geotransform[1] + self.rows * self.geotransform[2]
        self.se_sc = self.geotransform[3] + self.columns * self.geotransform[4] + self.rows * self.geotransform[5]
        self.sw_fc = self.geotransform[0] + 0.0 * self.geotransform[1] + self.rows * self.geotransform[2]
        self.sw_sc = self.geotransform[3] + 0.0 * self.geotransform[4] + self.rows * self.geotransform[5]
        self.number_of_bands = self.data_set.RasterCount
        self.scale_by_band = {}
        self.offset_by_band = {}
        self.min_value_by_band = {}
        self.max_value_by_band = {}
        self.raster_by_band = {}
        self.gdal_data_type_by_band = {}
        self.no_data_value_by_band = {}
        self.data_by_band = {}
        for i in range(self.number_of_bands):
            self.raster_by_band[i] = self.data_set.GetRasterBand(i+1)
            self.gdal_data_type_by_band[i] = self.raster_by_band[i].DataType
            self.scale_by_band[i] = self.raster_by_band[i].GetScale()
            self.offset_by_band[i] = self.raster_by_band[i].GetOffset()
            # self.gdal_data_type_by_band[idx] = gdal.GetDataTypeName(band.DataType)
            self.data_by_band[i] = None
            self.no_data_value_by_band[i] = self.raster_by_band[i].GetNoDataValue()
            min_value, max_value = self.raster_by_band[i].ComputeRasterMinMax(True)
            self.min_value_by_band[i] = min_value * self.scale_by_band[i] + self.offset_by_band[i]
            self.max_value_by_band[i] = max_value * self.scale_by_band[i] + self.offset_by_band[i]
            if load_data:
                self.data_by_band[i] = self.raster_by_band[i].ReadAsArray() # in original data type
            yo = 1
        self.file_path = file_path
        return str_error

