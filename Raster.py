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
        # precision -1 for no try to optimize data type
        # precision 0 for round as integer float values
        self.crs_tools = CRSsTools()
        self.data_set = None
        self.precision = precision
        self.dbl_to_int = 10. ** precision
        self.int_to_dbl = 1.0 / self.dbl_to_int
        self.crs = None
        self.crs_by_user = None # used in CRSs operations if exists
        self.crs_epsg_code = None
        self.vertical_crs_epsg_code = None
        self.crs_id = None
        self.crs_id_by_user = None # used in CRSs operations if exists
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
        self.gdal_scale_by_band = {}
        self.gdal_offset_by_band = {}
        self.scale_by_band = {}
        self.offset_by_band = {}
        self.min_value_by_band = {}
        self.max_value_by_band = {}
        self.raster_by_band = {}
        self.gdal_data_type_by_band = {}
        self.no_data_value_by_band = {}
        self.array_by_band = {}
        self.file_path = None
        self.bicubic_coef_matrix = None

    def bicubic_coefs(self, r, c, band_position): # https://en.wikipedia.org/wiki/Bicubic_interpolation
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
        if not band_position in self.array_by_band:
            str_error = ('Position: {} is not in raster data bands container'.format(str(band_position)))
            return str_error, coefs
        data = self.array_by_band[band_position]
        no_masked_values = []
        no_masked_values_mean = 0.
        for i in range(r - 1 , r + 3):
            for j in range(c - 1, c + 3):
                if not np.ma.is_masked(data[i, j]):
                    no_masked_values.append(data[i, j])
                    no_masked_values_mean = no_masked_values_mean + data[i, j]
        if len(no_masked_values) == 0:
            str_error = ('Not exists valid values for posidion: [row = {}, col = {}]\nin band position: {}'
                         .format(str(r), str(c), str(band_position)))
            return str_error, coefs
        # mode_value = mode(no_masked_values)
        mean_value = no_masked_values_mean / len(no_masked_values)
        values = np.zeros((4, 4))
        for i in range(r - 1 , r + 3):
            for j in range(c - 1, c + 3):
                value = data[i, j]
                if np.ma.is_masked(data[i, j]):
                    value = mean_value
                values[i - (r - 1), j - (c - 1)] = (value * self.scale_by_band[band_position]
                                                    + self.offset_by_band[band_position])

        f_0_0 = values[1, 1]
        # f_0_0 = data[r, c]

        f_1_0 = values[2, 1]
        # f_1_0 = data[r + 1, c]

        f_0_1 = values[1, 2]
        # f_0_1 = data[r, c + 1]

        f_1_1 = values[2, 2]
        # f_1_1 = data[r + 1, c + 1]

        f_x_0_0 = (values[2, 1] - values[0, 1]) / 2.  # df/dx central diff
        # f_x_0_0 = (data[r + 1, c] - data[r - 1, c]) / 2.  # df/dx central diff

        f_x_1_0 = (values[3, 1] - values[1, 1]) / 2.  # df/dx central diff
        # f_x_1_0 = (data[r + 2, c] - data[r, c]) / 2.  # df/dx central diff

        f_x_0_1 = (values[2, 2] - values[0, 2]) / 2.  # df/dx central diff
        # f_x_0_1 = (data[r + 1, c + 1] - data[r - 1, c + 1]) / 2.  # df/dx central diff

        f_x_1_1 = (values[3, 2] - values[1, 2]) / 2.  # df/dx central diff
        # f_x_1_1 = (data[r + 2, c + 1] - data[r, c + 1]) / 2.  # df/dx central diff

        f_y_0_0 = (values[1, 2] - values[1, 0]) / 2.  # df/dy central diff
        # f_y_0_0 = (data[r, c + 1] - data[r, c - 1]) / 2.  # df/dy central diff

        f_y_1_0 = (values[2, 2] - values[2, 0]) / 2.  # df/dy central diff
        # f_y_1_0 = (data[r + 1, c + 1] - data[r + 1, c - 1]) / 2.  # df/dy central diff

        f_y_0_1 = (values[1, 3] - values[1, 1]) / 2.  # df/dy central diff
        # f_y_0_1 = (data[r, c + 2] - data[r, c]) / 2.  # df/dy central diff

        f_y_1_1 = (values[2, 3] - values[2, 1]) / 2.  # df/dy central diff
        # f_y_1_1 = (data[r + 1, c + 2] - data[r + 1, c]) / 2.  # df/dy central diff

        f_x_y_0_0 = (values[2, 2] + values[0, 0] - values[2, 0] - values[0, 2]) / 2.  # d2f/(dxdy] central diff
        # f_x_y_0_0 = (data[r + 1, c + 1] + data[r - 1, c - 1] - data[r + 1, c - 1] - data[
        #     r - 1, c + 1]) / 2.  # d2f/(dxdy] central diff

        f_x_y_1_0 = (values[3, 2] + values[1, 0] - values[3, 0] - values[1, 2]) / 2.
        # f_x_y_1_0 = (data[r + 2, c + 1] + data[r, c - 1] - data[r + 2, c - 1] - data[r, c + 1]) / 2.

        f_x_y_0_1 = (values[2, 3] + values[0, 1] - values[2, 1] - values[0, 3]) / 2.
        # f_x_y_0_1 = (data[r + 1, c + 2] + data[r - 1, c] - data[r + 1, c] - data[r - 1, c + 2]) / 2.

        f_x_y_1_1 = (values[3, 3] + values[1, 1] - values[3, 1] - values[1, 3]) / 2.
        # f_x_y_1_1 = (data[r + 2, c + 2] + data[r, c] - data[r + 2, c] - data[r, c + 2]) / 2.

        f_matrix = np.zeros((4, 4))
        f_matrix[0][0] = f_0_0
        f_matrix[0][1] = f_0_1
        f_matrix[0][2] = f_y_0_0
        f_matrix[0][3] = f_y_0_1
        f_matrix[1][0] = f_1_0
        f_matrix[1][1] = f_1_1
        f_matrix[1][2] = f_y_1_0
        f_matrix[1][3] = f_y_1_1
        f_matrix[2][0] = f_x_0_0
        f_matrix[2][1] = f_x_0_1
        f_matrix[2][2] = f_x_y_0_0
        f_matrix[2][3] = f_x_y_0_1
        f_matrix[3][0] = f_x_1_0
        f_matrix[3][1] = f_x_1_1
        f_matrix[3][2] = f_x_y_1_0
        f_matrix[3][3] = f_x_y_1_1
        int_matrix = np.matrix('1 0 0 0;1 1 1 1;0 1 0 0;0 1 2 3')
        inv_int_matrix = np.linalg.inv(int_matrix)
        coef = inv_int_matrix * f_matrix * inv_int_matrix.transpose()
        # x = np.zeros(16)
        # x[0] = data[r, c]
        # x[1] = data[r + 1, c]
        # x[2] = data[r, c + 1]
        # x[3] = data[r + 1, c + 1]
        # x[4] = (data[r + 1, c] - data[r - 1, c]) / 2.  # df/dx central diff
        # x[5] = (data[r + 2, c] - data[r, c]) / 2.  # df/dx central diff
        # x[6] = (data[r + 1, c + 1] - data[r - 1, c + 1]) / 2.  # df/dx central diff
        # x[7] = (data[r + 2, c + 1] - data[r, c + 1]) / 2.  # df/dx central diff
        # x[8] = (data[r, c + 1] - data[r, c - 1]) / 2.  # df/dy central diff
        # x[9] = (data[r + 1, c + 1] - data[r + 1, c - 1]) / 2.  # df/dy central diff
        # x[10] = (data[r, c + 2] - data[r, c]) / 2.  # df/dy central diff
        # x[11] = (data[r + 1, c + 2] - data[r + 1, c]) / 2.  # df/dy central diff
        # x[12] = (data[r + 1, c + 1] + data[r - 1, c - 1] - data[r + 1, c - 1] - data[
        #     r - 1, c + 1]) / 2.  # d2f/(dxdy] central diff
        # x[13] = (data[r + 2, c + 1] + data[r, c - 1] - data[r + 2, c - 1] - data[r, c + 1]) / 2.
        # x[14] = (data[r + 1, c + 2] + data[r - 1, c] - data[r + 1, c] - data[r - 1, c + 2]) / 2.
        # x[15] = (data[r + 2, c + 2] + data[r, c] - data[r + 2, c] - data[r, c + 2]) / 2.
        # self.set_bicubic_coef_matrix()
        # alpha = self.bicubic_coef_matrix * x
        # coef = alpha.transpose()
        return str_error, coef

    def bilinear_coefs(self, r, c, band_position): # https://en.wikipedia.org/wiki/Bilinear_interpolation
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
        if not band_position in self.array_by_band:
            str_error = ('Position: {} is not in raster data bands container'.format(str(band_position)))
            return str_error, coefs
        data = self.array_by_band[band_position]
        no_masked_values = []
        no_masked_values_mean = 0.
        for i in range(r, r + 2):
            for j in range(c, c + 2):
                if not np.ma.is_masked(data[i, j]):
                    no_masked_values.append(data[i, j])
                    no_masked_values_mean = no_masked_values_mean + data[i, j]
        if len(no_masked_values) == 0:
            str_error = ('Not exists valid values for posidion: [row = {}, col = {}]\nin band position: {}'
                         .format(str(r), str(c), str(band_position)))
            return str_error, coefs
        # mode_value = mode(no_masked_values)
        mean_value = no_masked_values_mean / len(no_masked_values)
        values = np.zeros((2, 2))
        for i in range(r , r + 2):
            for j in range(c, c + 2):
                value = data[i, j]
                if np.ma.is_masked(data[i, j]):
                    value = mean_value
                values[i - r, j - c] = (value * self.scale_by_band[band_position]
                                        + self.offset_by_band[band_position])
        coefs = np.zeros((2,2))
        coefs[0][0] = values[0][0]
        # coefs[0][0] = data[r][c]
        coefs[1][0] = values[1][0] - values[0][0]
        # coefs[1][0] = data[r + 1][c] - data[r][c]
        coefs[0][1] = values[0][1] - values[0][0]
        # coefs[0][1] = data[r][c + 1] - data[r][c]
        coefs[1][1] = (values[1][1] + values[0][0]) - (values[1][0] + values[0][1])
        # coefs[1][1] = (data[r + 1][c + 1] + data[r][c]) - (data[r + 1][c] + data[r][c + 1])
        return str_error, coefs

    def get_crs_id(self):
        crs_id = self.crs_id
        if self.crs_id_by_user:
            crs_id = self.crs_id_by_user
        return crs_id

    def get_pixel_value(self, col, row, band_position):
        str_error = ''
        value = None
        if not self.data_set:
            str_error = ('Data set is not initialized')
            return str_error, value
        if not band_position in self.raster_by_band:
            str_error = ('Position: {} is not in raster bands container'.format(str(band_position)))
            return str_error, value
        if not band_position in self.array_by_band:
            str_error = self.load(True,[band_position])
            if str_error:
                str_error = ('Loading band position: {}\nerror:\n{}'.format(str(band_position), str_error))
                return str_error, value
        data = self.array_by_band[band_position]
        if col == self.columns:
            col = col - 1
        if row == self.rows:
            row = row - 1
        if col < 0 or col > (self.columns - 1) or row < 0 or row > (self.rows - 1):
            str_error = ('Pixel: [{}, {}]\nis out of raster DEM:\n{}'.format(str(col), str(row), self.file_path))
            return str_error, value
        if np.ma.is_masked(data[row, col]):
           return str_error, value
        value = data[row, col] * self.scale_by_band[band_position] + self.offset_by_band[band_position]
        return str_error, value

    def interpolate(self,
                    coordinates,
                    crs_id,
                    band_position,
                    interpolation_method):
        str_error = ''
        interpolated_value = None
        if not isinstance(coordinates, list):
            str_error = ('Argument coordinates must be a list and is a: {}'.format(str(type(coordinates))))
            return str_error, interpolated_value
        if len(coordinates) < 2:
            str_error = ('Argument coordinates must be a list with two values at leas')
            return str_error, interpolated_value
        if not isinstance(crs_id, str):
            str_error = ('Argument crs_id must be a string and is a: {}'.format(str(type(crs_id))))
            return str_error, interpolated_value
        if (interpolation_method.casefold() != defs_gdal.INTERPOLATION_METHOD_BICUBIC.casefold()
                and interpolation_method.casefold() != defs_gdal.INTERPOLATION_METHOD_BILINEAR.casefold()):
            str_error = ('Argument interpolation method bust be {} or {}'.
                         format(defs_gdal.INTERPOLATION_METHOD_BICUBIC, defs_gdal.INTERPOLATION_METHOD_BILINEAR))
            return str_error, interpolated_value
        if not self.data_set:
            str_error = ('Data set is not initialized')
            return str_error, interpolated_value
        if not band_position in self.raster_by_band:
            str_error = ('Position: {} is not in raster bands container'.format(str(band_position)))
            return str_error, interpolated_value
        if not band_position in self.array_by_band:
            str_error = self.load(True,[band_position])
            if str_error:
                str_error = ('Loading band position: {}\nerror:\n{}'.format(str(band_position), str_error))
                return str_error, interpolated_value
        if len(coordinates) == 2:
            coordinates.append(0.)
        coordinates_in_raster_crs = [coordinates] # list of list
        if self.crs_id != crs_id:
            str_error = self.crs_tools.operation(crs_id, self.crs_id, coordinates_in_raster_crs)
            if str_error:
                if str_error:
                    str_error = ('Converting coordinates to raster CRS, error:\n{}'.format(str_error))
                    return str_error, interpolated_value
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
                return str_error, interpolated_value
        elif interpolation_method.casefold() == defs_gdal.INTERPOLATION_METHOD_BILINEAR.casefold():
            str_error, coefs = self.bilinear_coefs(r, c, band_position)
            if str_error:
                str_error = ('Getting bilinear coefficients, error:\n{}'.format(str_error))
                return str_error, interpolated_value
        coefs_columns = coefs.shape[1]
        x = np.ones((1, coefs_columns))
        y = np.ones((coefs_columns, 1))
        for i in range(1, coefs_columns):
            x[0][i] = dr ** i
            y[i][0] = dc ** i
        tmp = x * coefs * y
        interpolated_value = tmp[0][0]
        interpolated_value = interpolated_value.item()
        return str_error, interpolated_value

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
            return str_error, du_dr, du_dc
        if not band_position in self.raster_by_band:
            str_error = ('Position: {} is not in raster bands container'.format(str(band_position)))
            return str_error, du_dr, du_dc
        if not band_position in self.array_by_band:
            str_error = self.load(True,[band_position])
            if str_error:
                str_error = ('Loading band position: {}\nerror:\n{}'.format(str(band_position), str_error))
                return str_error, du_dr, du_dc
        if len(coordinates) == 2:
            coordinates.append(0.)
        coordinates_in_raster_crs = [coordinates] # list of list
        if self.crs_id != crs_id:
            str_error = self.crs_tools.operation(crs_id, self.crs_id, coordinates_in_raster_crs)
            if str_error:
                if str_error:
                    str_error = ('Converting coordinates to raster CRS, error:\n{}'.format(str_error))
                    return str_error, du_dr, du_dc
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
                return str_error, du_dr, du_dc
        elif interpolation_method.casefold() == defs_gdal.INTERPOLATION_METHOD_BILINEAR.casefold():
            str_error, coefs = self.bilinear_coefs(r, c, band_position)
            if str_error:
                str_error = ('Getting bilinear coefficients, error:\n{}'.format(str_error))
                return str_error, du_dr, du_dc
        coefs_columns = coefs.shape[1]
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
        du_dr = du_dr.item()
        tmp = x * coefs * dy
        du_dc = tmp[0][0]
        du_dc = du_dc.item()
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
            if not self.array_by_band[i]:
                try:
                    self.array_by_band[i] = self.raster_by_band[i].ReadAsMaskedArray()  # in original data type
                    # value_0 = self.array_by_band[i][6328, 6475]
                    # yo = 1
                except Exception as e:
                    str_error = 'GDAL Error: ' + e.args[0]
                if self.precision != -1:
                    min_value_as_integer = math.floor(self.min_value_by_band[i] * self.dbl_to_int)
                    max_value_as_integer = math.ceil(self.max_value_by_band[i] * self.dbl_to_int)
                    range_as_integer = max_value_as_integer - min_value_as_integer
                    new_dtype = np.uint8
                    if range_as_integer > (2 ** 8):
                        new_dtype = np.uint16
                    if range_as_integer > (2 ** 16):
                        new_dtype = np.uint32
                    if range_as_integer > (2 ** 32):
                        new_dtype = np.uint64
                    if range_as_integer > (2 ** 64):
                        new_dtype = np.float32
                    gdal_data_type = self.gdal_data_type_by_band[i]
                    gdal_scale = self.gdal_scale_by_band[i]
                    gdal_offset = self.gdal_offset_by_band[i]
                    array_type = self.array_by_band[i].dtype
                    n_bytes = np.dtype(array_type).itemsize
                    new_bytes = np.dtype(new_dtype).itemsize
                    if new_bytes >= n_bytes:
                        continue
                    array_type_name = array_type.name
                    # value_1 = self.array_by_band[i][1210, 1877]
                    if not 'float' in array_type_name and (gdal_scale != 1 or gdal_offset != 0):
                        self.array_by_band[i] = self.array_by_band[i].astype('float32', copy = False)
                        if gdal_scale != 1:
                            self.array_by_band[i].__imul__(gdal_scale)
                            # value_2 = self.array_by_band[i][1210, 1877]
                        if gdal_offset != 0:
                            self.array_by_band[i].__iadd__(gdal_offset)
                            # value_3 = self.array_by_band[i][1210, 1877]
                    if not 'float' in array_type_name:
                        self.array_by_band[i] = self.array_by_band[i].astype('float32', copy = False)
                    if gdal_scale != 1:
                        self.array_by_band[i].__imul__(gdal_scale)
                        # value_2 = self.array_by_band[i][1210, 1877]
                    if gdal_offset != 0:
                        self.array_by_band[i].__iadd__(gdal_offset)
                        # value_3 = self.array_by_band[i][1210, 1877]
                    self.array_by_band[i].__imul__(self.dbl_to_int)
                    # # value_1 = self.array_by_band[i][6328, 6475]
                    # yo = 1
                    # value_4 = self.array_by_band[i][1210, 1877]
                    self.array_by_band[i].__iadd__(-1.* min_value_as_integer)
                    # value_2 = self.array_by_band[i][6328, 6475]
                    # yo = 1
                    # value_5 = self.array_by_band[i][1210, 1877]
                    self.array_by_band[i] = self.array_by_band[i].astype(new_dtype, copy=False)
                    # value_3 = self.array_by_band[i][6328, 6475]
                    # yo = 1
                    # value_6 = self.array_by_band[i][1210, 1877]
                    self.scale_by_band[i] = self.int_to_dbl
                    self.offset_by_band[i] = min_value_as_integer * self.int_to_dbl

                # ram = psutil.virtual_memory()
                # available_ram_in_bytes = ram.available
                # bytes_by_pixel = None
                # if self.gdal_data_type_by_band[i] in defs_gdal.gdal_bytes_by_type:
                #     bytes_by_pixel = defs_gdal.gdal_bytes_by_type[self.gdal_data_type_by_band[i]]
                # else:
                #     str_error = ('Invalid data type for band position: {}'.format(str(i)))
                #     return str_error
                # needed_memory_in_bytes = self.columns * self.rows * bytes_by_pixel
                # if needed_memory_in_bytes > (available_ram_in_bytes * defs_gdal.MAX_PERCENTAGE_AVAILABLE_RAM_TO_USE / 100.):
                #     str_error = ('There are no enough available RAM to load band position: {}'.format(str(i)))
                #     return str_error
                # try:
                #     self.array_by_band[i] = self.raster_by_band[i].ReadAsMaskedArray()  # in original data type
                # except Exception as e:
                #     str_error = 'GDAL Error: ' + e.args[0]
        return str_error

    def set_crs_id_by_user(self,
                           crs_id):
        str_error = ''
        str_error, crs = self.crs_tools.get_crs_from_id(crs_id)
        if str_error:
            return str_error
        self.crs_id_by_user = crs_id
        self.crs_by_user = crs
        return

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
        self.crs = None
        try:
            self.crs = self.data_set.GetSpatialRef()
        except Exception as e:
            str_error = 'GDAL Error: ' + e.args[0]
        srs_unit = ""
        if self.crs: # compound is pending
            srs_as_projjson = ''
            try:
                srs_as_projjson = json.loads(self.crs.ExportToPROJJSON())
            except Exception as e:
                str_error = 'GDAL Error: ' + e.args[0]
            # srs_as_wkt = self.crs.ExportToPrettyWkt()
            if srs_as_projjson:
                is_compound = False
                try:
                    is_compound = self.crs.IsCompound()
                except Exception as e:
                    str_error = 'GDAL Error: ' + e.args[0]
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
                    else:
                        if "source_crs" in srs_as_projjson:
                            if "id" in srs_as_projjson["source_crs"]:
                                id = srs_as_projjson["source_crs"]["id"]
                                authority = id["authority"]
                                code = id["code"]
                                if authority.casefold() == 'EPSG'.casefold():
                                    self.crs_id = ("{}:{}".format(authority, str(code)))
                                    self.crs_epsg_code = code
                    # srs_unit = " " + srs_as_projjson["coordinate_system"]["axis"][0]["unit"]
        if not self.crs_id and self.crs:
            authority = ''
            try:
                authority = self.crs.GetAuthorityName(None)
            except Exception as e:
                str_error = 'GDAL Error: ' + e.args[0]
            if authority.casefold() == 'EPSG'.casefold():
                code = ''
                try:
                    code = srs.GetAuthorityCode(None)
                except Exception as e:
                    str_error = 'GDAL Error: ' + e.args[0]
                self.crs_id = ("{}:{}".format(authority, str(code)))
                self.crs_epsg_code = code
        self.geotransform = None
        try:
            self.geotransform = self.data_set.GetGeoTransform()
        except Exception as e:
            str_error = 'GDAL Error: ' + e.args[0]
        if not self.geotransform:
            str_error = ('Invalid geotransform in raster data source:\n{}'.format(file_path))
            return str_error
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
        self.gdal_scale_by_band = {}
        self.gdal_offset_by_band = {}
        self.scale_by_band = {}
        self.offset_by_band = {}
        self.min_value_by_band = {}
        self.max_value_by_band = {}
        self.raster_by_band = {}
        self.gdal_data_type_by_band = {}
        self.no_data_value_by_band = {}
        self.array_by_band = {}
        for i in range(self.number_of_bands):
            self.raster_by_band[i] = self.data_set.GetRasterBand(i+1)
            self.gdal_data_type_by_band[i] = self.raster_by_band[i].DataType
            self.gdal_scale_by_band[i] = self.raster_by_band[i].GetScale() # value or Non
            if not self.gdal_scale_by_band[i]:
                self.gdal_scale_by_band[i] = 1
            self.scale_by_band[i] = self.gdal_scale_by_band[i]
            self.gdal_offset_by_band[i] = self.raster_by_band[i].GetOffset() # value or None
            if not self.gdal_offset_by_band[i]:
                self.gdal_offset_by_band[i] = 0
            self.offset_by_band[i] = self.gdal_offset_by_band[i]
            # self.gdal_data_type_by_band[idx] = gdal.GetDataTypeName(band.DataType)
            self.array_by_band[i] = None
            self.no_data_value_by_band[i] = self.raster_by_band[i].GetNoDataValue()
            min_value, max_value = self.raster_by_band[i].ComputeRasterMinMax(False)
            self.min_value_by_band[i] = min_value * self.gdal_scale_by_band[i] + self.gdal_offset_by_band[i]
            self.max_value_by_band[i] = max_value * self.gdal_scale_by_band[i] + self.gdal_offset_by_band[i]
        self.file_path = file_path
        return str_error


