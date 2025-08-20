# authors:
# David Hernandez Lopez, david.hernandez@uclm.es

import os, sys
from osgeo import gdal, osr, ogr
import json
import numpy as np
import psutil
import math

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
        self.vertical_crs_epsg_code = None
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
        self.bicubic_coef_matrix = None

    def bicubic_coefs(self, r, c, band_position):
        str_error = ''
        coefs = None
        if not self.data_set:
            str_error = ('Data set is not initialized')
            return str_error, coefs
        if r < 0 or r > (self.rows - 3):
            str_error = ('Row: {} is out of domain [{}, {}]'.format(str(r), str(0), str(self.rows - 3)))
            return str_error, coefs
        if c < 0 or c > (self.columns - 3):
            str_error = ('Column: {} is out of domain [{}, {}]'.format(str(c), str(0), str(self.columns - 3)))
            return str_error, coefs
        if not band_position in self.raster_by_band:
            str_error = ('Position: {} is not in raster bands container'.format(str(band_position)))
            return str_error, coefs
        if not band_position in self.data_by_band:
            str_error = ('Position: {} is not in raster data bands container'.format(str(band_position)))
            return str_error, coefs
        data = self.data_by_band[band_position]
        x = np.zeros(16)
        x[0] = data[r, c]
        x[1] = data[r + 1, c]
        x[2] = data[r, c + 1]
        x[3] = data[r + 1, c + 1]
        x[4] = (data[r + 1, c] - data[r - 1, c]) / 2.  # df/dx central diff
        x[5] = (data[r + 2, c] - data[r, c]) / 2.  # df/dx central diff
        x[6] = (data[r + 1, c + 1] - data[r - 1, c + 1]) / 2.  # df/dx central diff
        x[7] = (data[r + 2, c + 1] - data[r, c + 1]) / 2.  # df/dx central diff
        x[8] = (data[r, c + 1] - data[r, c - 1]) / 2.  # df/dy central diff
        x[9] = (data[r + 1, c + 1] - data[r + 1, c - 1]) / 2.  # df/dy central diff
        x[10] = (data[r, c + 2] - data[r, c]) / 2.  # df/dy central diff
        x[11] = (data[r + 1, c + 2] - data[r + 1, c]) / 2.  # df/dy central diff
        x[12] = (data[r + 1, c + 1] + data[r - 1, c - 1] - data[r + 1, c - 1] - data[
            r - 1, c + 1]) / 2.  # d2f/(dxdy] central diff
        x[13] = (data[r + 2, c + 1] + data[r, c - 1] - data[r + 2, c - 1] - data[r, c + 1]) / 2.
        x[14] = (data[r + 1, c + 2] + data[r - 1, c] - data[r + 1, c] - data[r - 1, c + 2]) / 2.
        x[15] = (data[r + 2, c + 2] + data[r, c] - data[r + 2, c] - data[r, c + 2]) / 2.
        self.set_bicubic_coef_matrix()
        alpha = self.bicubic_coef_matrix * x
        coef = alpha.transpose()
        return str_error, coef

    def bilinear_coefs(self, r, c, band_position):
        str_error = ''
        coefs = None
        if not self.data_set:
            str_error = ('Data set is not initialized')
            return str_error, coefs
        if r < 0 or r > (self.rows - 2):
            str_error = ('Row: {} is out of domain [{}, {}]'.format(str(r), str(0), str(self.rows - 2)))
            return str_error, coefs
        if c < 0 or c > (self.columns - 2):
            str_error = ('Column: {} is out of domain [{}, {}]'.format(str(c), str(0), str(self.columns - 2)))
            return str_error, coefs
        if not band_position in self.raster_by_band:
            str_error = ('Position: {} is not in raster bands container'.format(str(band_position)))
            return str_error, coefs
        if not band_position in self.data_by_band:
            str_error = ('Position: {} is not in raster data bands container'.format(str(band_position)))
            return str_error, coefs
        data = self.data_by_band[band_position]
        coefs = np.zeros((2,2))
        coefs[0][0] = data[r][c]
        coefs[1][0] = data[r + 1][c] - data[r][c]
        coefs[0][1] = data[r][c + 1] - data[r][c]
        coefs[1][1] = (data[r + 1][c + 1] + data[r][c]) - (data[r + 1][c] + data[r][c + 1])
        return str_error, coefs

    def interpolate_derivate(self,
                             coordinates,
                             crs_id,
                             band_position,
                             interpolation_method):
        str_error = ''
        du_dr = None
        du_dc = None
        if not isinstance(coordinates, list):
            str_error = ('Argument coordinates must be a list and is a: {}'.format(str(type(coordinates))))
            return str_error, du_dr, du_dc
        if len(coordinates) < 2:
            str_error = ('Argument coordinates must be a list with two values at leas')
            return str_error, du_dr, du_dc
        if not isinstance(crs_id, str):
            str_error = ('Argument crs_id must be a string and is a: {}'.format(str(type(crs_id))))
            return str_error, du_dr, du_dc
        if (interpolation_method.casefold() != defs_gdal.INTERPOLATION_METHOD_BICUBIC.casefold()
                and interpolation_method.casefold() != defs_gdal.INTERPOLATION_METHOD_BILINEAR.casefold()):
            str_error = ('Argument interpolation method bust be {} or {}'.
                         format(defs_gdal.INTERPOLATION_METHOD_BICUBIC, defs_gdal.INTERPOLATION_METHOD_BILINEAR))
            return str_error, du_dr, du_dc
        if not self.data_set:
            str_error = ('Data set is not initialized')
            return str_error
        if not band_position in self.raster_by_band:
            str_error = ('Position: {} is not in raster bands container'.format(str(band_position)))
            return str_error
        if not band_position in self.data_by_band:
            str_error = self.load(True,[band_position])
            if str_error:
                str_error = ('Loading band position: {}\nerror:\n{}'.format(str(band_position), str_error))
                return str_error
        if len(coordinates) == 2:
            coordinates.append(0.)
        coordinates_in_raster_crs = [coordinates] # list of list
        if self.crs_id != crs_id:
            str_error = self.crs_tools.operation(crs_id, self.crs_id, coordinates_in_raster_crs)
            if str_error:
                if str_error:
                    str_error = ('Converting coordinates to raster CRS, error:\n{}'.format(str_error))
                    return str_error
        fc = coordinates_in_raster_crs[0][0]
        sc = coordinates_in_raster_crs[0][1]
        col = (fc - self.nw_fc) / self.size_fc
        row = (self.nw_sc - sc) / self.size_sc
        r = math.floor(row)
        c = math.floor(col)
        dr = row - r
        dc = col - c
        # Sanity check for rounding errors
        while dr < 0.:
            dr += 1.0
            r -= 1
        while dr >= 1.:
            dr -= 1.0
            r += 1
        while dc < 0.:
            dc += 1.0
            c -= 1
        while dc >= 1.:
            dc -= 1.0
            c += 1
        coefs = None
        if interpolation_method.casefold() == defs_gdal.INTERPOLATION_METHOD_BICUBIC.casefold():
            str_error, coefs = self.bicubic_coefs(r, c, band_position)
            if str_error:
                str_error = ('Getting bicubic coefficients, error:\n{}'.format(str_error))
                return str_error
        elif interpolation_method.casefold() == defs_gdal.INTERPOLATION_METHOD_BILINEAR.casefold():
            str_error, coefs = self.bilinear_coefs(r, c, band_position)
            if str_error:
                str_error = ('Getting bilinear coefficients, error:\n{}'.format(str_error))
                return str_error
        (coefs_rows, coefs_columns) = coefs.shape()
        dx = np.zeros((1, coefs_columns))
        dy = np.zeros((coefs_columns, 1))
        x = np.ones((1, coefs_columns))
        y = np.ones((coefs_columns, 1))
        for i in range(1, coefs_columns):
            x[0][i] = dr ** i
            dx[0][i] = (dr ** (i - 1)) * i
            y[i][0] = dc ** i
            dy[i][0] = (dc ** (i - 1)) * i
        tmp = dx * coefs * y
        du_dr = tmp[0][0]
        tmp = x * coefs * dy
        du_dc = tmp[0][0]
        # for(i=1; i<dim; i++) {
        #   x(0,i) = pow(dr,i);
        #   dx(0,i) = pow(dr,i-1)*i;
        #   y(i,0) = pow(dc,i);
        #   dy(i,0) = pow(dc,i-1)*i;
        # }
        # tmp = dx*coefs*y;
        # di_dr = tmp(0,0);
        # tmp = x*coefs*dy;
        # di_dc = tmp(0,0);

        return str_error, du_dr, du_dc

    def load(self,
             fully = True,
             bands = None):
        str_error = ''
        if not self.data_set:
            str_error = ('Data set is not initialized')
            return str_error
        if bands:
            if not isinstance(bands, list):
                str_error = ('Argument bands must be a list and is a: {}'.format(str(type(bands))))
                return str_error
        else:
            bands = []
            for i in range(self.number_of_bands):
                bands.append(i)
        for j in range(len(bands)):
            i = bands[j]
            if not i in self.raster_by_band:
                str_error = ('Position: {} is not in raster bands container'.format(str(i)))
                return str_error
            if not self.data_by_band[i]:
                ram = psutil.virtual_memory()
                available_ram_in_bytes = ram.available
                bytes_by_pixel = None
                if self.gdal_data_type_by_band[i] in defs_gdal.gdal_bytes_by_type:
                    bytes_by_pixel = defs_gdal.gdal_bytes_by_type[self.gdal_data_type_by_band[i]]
                else:
                    str_error = ('Invalid data type for band position: {}'.format(str(i)))
                    return str_error
                needed_memory_in_bytes = self.columns * self.rows * bytes_by_pixel
                if needed_memory_in_bytes > (available_ram_in_bytes * defs_gdal.MAX_PERCENTAGE_AVAILABLE_RAM_TO_USE / 100.):
                    str_error = ('There are no enough available RAM to load band position: {}'.format(str(i)))
                    return str_error
                try:
                    self.data_by_band[i] = self.raster_by_band[i].ReadAsArray()  # in original data type
                except Exception as e:
                    str_error = 'GDAL Error: ' + e.args[0]
        return str_error

    def set_from_file(self,
                      file_path):
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
        self.vertical_crs_epsg_code = None
        self.crs_id = None
        self.crs = self.data_set.GetSpatialRef()
        srs_unit = ""
        if self.crs: # compound is pending
            srs_as_projjson = json.loads(self.crs.ExportToPROJJSON())
            srs_as_wkt = self.crs.ExportToPrettyWkt()
            is_compound = self.crs.IsCompound()
            if is_compound:
                str_error, self.crs_id, self.crs_epsg_code, self.vertical_crs_epsg_code =(
                    self.crs_tools.get_compound_crs_from_json(srs_as_projjson))
                if str_error:
                    return str_error
            else:
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
        self.size_fc = abs(self.geotransform[1])
        self.size_sc = abs(self.geotransform[5])
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
        self.file_path = file_path
        return str_error

    def set_bicubic_coef_matrix(self):
        if not self.bicubic_coef_matrix:
            self.bicubic_coef_matrix = np.zeros((4, 4))
            self.bicubic_coef_matrix[0][0] = 1
            self.bicubic_coef_matrix[1][4] = 1
            self.bicubic_coef_matrix[2][0] = -3
            self.bicubic_coef_matrix[2][1] = 3
            self.bicubic_coef_matrix[2][4] = -2
            self.bicubic_coef_matrix[2][5] = -1
            self.bicubic_coef_matrix[3][0] = 2
            self.bicubic_coef_matrix[3][1] = -2
            self.bicubic_coef_matrix[3][4] = 1
            self.bicubic_coef_matrix[3][5] = 1
            self.bicubic_coef_matrix[4][8] = 1
            self.bicubic_coef_matrix[5][12] = 1
            self.bicubic_coef_matrix[6][8] = -3
            self.bicubic_coef_matrix[6][9] = 3
            self.bicubic_coef_matrix[6][12] = -2
            self.bicubic_coef_matrix[6][13] = -1
            self.bicubic_coef_matrix[7][8] = 2
            self.bicubic_coef_matrix[7][9] = -2
            self.bicubic_coef_matrix[7][12] = 1
            self.bicubic_coef_matrix[7][13] = 1
            self.bicubic_coef_matrix[8][0] = -3
            self.bicubic_coef_matrix[8][2] = 3
            self.bicubic_coef_matrix[8][8] = -2
            self.bicubic_coef_matrix[8][10] = -1
            self.bicubic_coef_matrix[9][4] = -3
            self.bicubic_coef_matrix[9][6] = 3
            self.bicubic_coef_matrix[9][12] = -2
            self.bicubic_coef_matrix[9][14] = -1
            self.bicubic_coef_matrix[10][0] = 9
            self.bicubic_coef_matrix[10][1] = -9
            self.bicubic_coef_matrix[10][2] = -9
            self.bicubic_coef_matrix[10][3] = 9
            self.bicubic_coef_matrix[10][4] = 6
            self.bicubic_coef_matrix[10][5] = 3
            self.bicubic_coef_matrix[10][6] = -6
            self.bicubic_coef_matrix[10][7] = -3
            self.bicubic_coef_matrix[10][8] = 6
            self.bicubic_coef_matrix[10][9] = -6
            self.bicubic_coef_matrix[10][10] = 3
            self.bicubic_coef_matrix[10][11] = -3
            self.bicubic_coef_matrix[10][12] = 4
            self.bicubic_coef_matrix[10][13] = 2
            self.bicubic_coef_matrix[10][14] = 2
            self.bicubic_coef_matrix[10][15] = 1
            self.bicubic_coef_matrix[11][0] = -6
            self.bicubic_coef_matrix[11][1] = 6
            self.bicubic_coef_matrix[11][2] = 6
            self.bicubic_coef_matrix[11][3] = -6
            self.bicubic_coef_matrix[11][4] = -3
            self.bicubic_coef_matrix[11][5] = -3
            self.bicubic_coef_matrix[11][6] = 3
            self.bicubic_coef_matrix[11][7] = 3
            self.bicubic_coef_matrix[11][8] = -4
            self.bicubic_coef_matrix[11][9] = 4
            self.bicubic_coef_matrix[11][10] = -2
            self.bicubic_coef_matrix[11][11] = 2
            self.bicubic_coef_matrix[11][12] = -2
            self.bicubic_coef_matrix[11][13] = -2
            self.bicubic_coef_matrix[11][14] = -1
            self.bicubic_coef_matrix[11][15] = -1
            self.bicubic_coef_matrix[12][0] = 2
            self.bicubic_coef_matrix[12][2] = -2
            self.bicubic_coef_matrix[12][8] = 1
            self.bicubic_coef_matrix[12][10] = 1
            self.bicubic_coef_matrix[13][4] = 2
            self.bicubic_coef_matrix[13][6] = -2
            self.bicubic_coef_matrix[13][12] = 1
            self.bicubic_coef_matrix[13][14] = 1
            self.bicubic_coef_matrix[14][0] = -6
            self.bicubic_coef_matrix[14][1] = 6
            self.bicubic_coef_matrix[14][2] = 6
            self.bicubic_coef_matrix[14][3] = -6
            self.bicubic_coef_matrix[14][4] = -4
            self.bicubic_coef_matrix[14][5] = -2
            self.bicubic_coef_matrix[14][6] = 4
            self.bicubic_coef_matrix[14][7] = 2
            self.bicubic_coef_matrix[14][8] = -3
            self.bicubic_coef_matrix[14][9] = 3
            self.bicubic_coef_matrix[14][10] = -3
            self.bicubic_coef_matrix[14][11] = 3
            self.bicubic_coef_matrix[14][12] = -2
            self.bicubic_coef_matrix[14][13] = -1
            self.bicubic_coef_matrix[14][14] = -2
            self.bicubic_coef_matrix[14][15] = -1
            self.bicubic_coef_matrix[15][0] = 4
            self.bicubic_coef_matrix[15][1] = -4
            self.bicubic_coef_matrix[15][2] = -4
            self.bicubic_coef_matrix[15][3] = 4
            self.bicubic_coef_matrix[15][4] = 2
            self.bicubic_coef_matrix[15][5] = 2
            self.bicubic_coef_matrix[15][6] = -2
            self.bicubic_coef_matrix[15][7] = -2
            self.bicubic_coef_matrix[15][8] = 2
            self.bicubic_coef_matrix[15][9] = -2
            self.bicubic_coef_matrix[15][10] = 2
            self.bicubic_coef_matrix[15][11] = -2
            self.bicubic_coef_matrix[15][12] = 1
            self.bicubic_coef_matrix[15][13] = 1
            self.bicubic_coef_matrix[15][14] = 1
            self.bicubic_coef_matrix[15][15] = 1


