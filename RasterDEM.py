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
        self.check_domain = True

    def bilinear_interpolation(self, inc_col, inc_row, values):
        str_error = ''
        elevation = None
        if len(values) != 4:
            str_error = 'the number of values must be 4'
            return str_error, elevation
        ul_value = values[0]
        ur_value = values[1]
        ll_value = values[2]
        lr_value = values[3]
        if not ul_value is None and not ur_value is None and not ll_value is None and not lr_value is None:
            elevation = (1.0 - inc_row) * (1.0 - inc_col) * float(ul_value)
            elevation += inc_col * (1.0 - inc_row) * float(ur_value)
            elevation += (1.0 - inc_col) * inc_row * float(ll_value)
            elevation += inc_col * inc_row * float(lr_value)
        elif not ul_value is None or not ur_value is None or not ll_value is None or not lr_value is None:
            elevation = 0.
            sum_weights = 0.
            if not ul_value is None:
                distance = np.sqrt(inc_row * inc_row + inc_col * inc_col)
                weight = 1.0 / (distance ** 2.0)
                elevation = elevation + weight * float(ul_value)
                sum_weights = sum_weights + weight
            if not ur_value is None:
                distance = np.sqrt(inc_row * inc_row + (1. - inc_col) * (1. - inc_col))
                weight = 1.0 / (distance ** 2.0)
                elevation = elevation + weight * float(ur_value)
                sum_weights = sum_weights + weight
            if not ll_value is None:
                distance = np.sqrt((1. - inc_row) * (1. - inc_row) + inc_col * inc_col)
                weight = 1.0 / (distance ** 2.0)
                elevation = elevation + weight * float(ll_value)
                sum_weights = sum_weights + weight
            if not lr_value is None:
                distance = np.sqrt((1. - inc_row) * (1. - inc_row) + (1. - inc_col) * (1. - inc_col))
                weight = 1.0 / (distance ** 2.0)
                elevation = elevation + weight * float(lr_value)
                sum_weights = sum_weights + weight
            elevation = elevation / sum_weights
        return str_error, elevation

    def get_elevation(self, fc, sc):
        str_error = ''
        elevation = None
        point_out_edge = fc < self.sw_fc or fc > self.ne_fc or sc < self.sw_sc or sc > self.ne_sc
        if point_out_edge and self.check_domain:
            str_error = ('Point: [{}, {}]\nis out of raster DEM:\n{}'.format(str(fc), str(sc), self.file_path))
            return str_error, elevation
        if not 0 in self.array_by_band:
            str_error = self.load()
            if str_error:
                str_error = ('Loading in memory raster DEM from file: {}\nError:\n{}'
                             .format(self.file_path, str_error))
                return str_error, elevation
        dbl_column = (fc - self.nw_fc) / self.size_fc
        dbl_row = (self.nw_sc - sc) / self.size_sc
        column = int(np.floor(dbl_column))
        row = int(np.floor(dbl_row))
        if point_out_edge:
            return self.get_elevation_for_no_data_point(column, row)
        if column == -1:
            column = 0
        if row == -1:
            row = 0
        if column > (self.columns - 2):
            column = self.columns - 2
        if row > (self.rows - 2):
            row = self.rows - 2
        inc_column = dbl_column - np.floor(dbl_column)
        inc_row = dbl_row - np.floor(dbl_row)
        values = []
        value_ul = None
        value_ur = None
        value_ll = None
        value_lr = None
        number_of_no_data_values = 0
        str_error, value_ul = self.get_pixel_value(column, row, 0)
        if value_ul is None:
            number_of_no_data_values = number_of_no_data_values + 1
        str_error, value_ur = self.get_pixel_value(column + 1, row, 0)
        if value_ur is None:
            number_of_no_data_values = number_of_no_data_values + 1
        str_error, value_ll = self.get_pixel_value(column, row + 1, 0)
        if value_ll is None:
            number_of_no_data_values = number_of_no_data_values + 1
        str_error, value_lr = self.get_pixel_value(column + 1, row + 1, 0)
        if value_lr is None:
            number_of_no_data_values = number_of_no_data_values + 1
        if number_of_no_data_values == 4:
            return self.get_elevation_for_no_data_point(column, row)
        values.append(value_ul)
        values.append(value_ur)
        values.append(value_ll)
        values.append(value_lr)
        return self.bilinear_interpolation(inc_column, inc_row, values)

    def get_elevation_for_no_data_point(self, col, row):
        str_error = ''
        elevation = None
        if not 0 in self.array_by_band:
            str_error = self.load()
            if str_error:
                str_error = ('Loading in memory raster DEM from file: {}\nError:\n{}'
                             .format(self.file_path, str_error))
                return str_error, elevation
        data = self.array_by_band[0]
        min_distance = 10000000000.0
        computed_distance = False
        find_col = -1
        find_row = -1
        # backward column process
        col_search = col
        if col_search > (self.columns - 1):
            col_search = self.columns - 1
        while col_search >= 0:
            if computed_distance and abs(col - col_search) > min_distance:
                break
            # up row process
            row_search = row
            if row_search > (self.rows - 1):
                row_search = self.rows - 1
            while row_search >= 0:
                if computed_distance and abs(row - row_search) > min_distance:
                    break
                if not np.ma.is_masked(data[row_search, col_search]):
                    value = data[row_search, col_search] * self.scale_by_band[0] + self.offset_by_band[0]
                    distance = np.sqrt((col - col_search) ** 2. + (row - row_search) ** 2.)
                    computed_distance = True
                    if distance < min_distance:
                        min_distance = distance
                        find_col = col_search
                        find_row = row_search
                        elevation = value
                        break
                row_search = row_search - 1
            # down row process
            row_search = row + 1
            if row_search > (self.rows - 1):
                row_search = self.rows - 1
            while row_search <= (self.rows - 1):
                if computed_distance and abs(row - row_search) > min_distance:
                    break
                if not np.ma.is_masked(data[row_search, col_search]):
                    value = data[row_search, col_search] * self.scale_by_band[0] + self.offset_by_band[0]
                    distance = np.sqrt((col - col_search) ** 2. + (row - row_search) ** 2.)
                    computed_distance = True
                    if distance < min_distance:
                        min_distance = distance
                        find_col = col_search
                        find_row = row_search
                        elevation = value
                        break
                row_search = row_search + 1
            col_search = col_search - 1
        # forward column process
        col_search = col + 1
        if col_search > (self.columns - 1):
            col_search = self.columns - 1
        while col_search <= (self.columns - 1):
            if computed_distance and abs(col - col_search) > min_distance:
                break
            # up row process
            row_search = row
            if row_search > (self.rows - 1):
                row_search = self.rows - 1
            while row_search >= 0:
                if computed_distance and abs(row - row_search) > min_distance:
                    break
                if not np.ma.is_masked(data[row_search, col_search]):
                    value = data[row_search, col_search] * self.scale_by_band[0] + self.offset_by_band[0]
                    distance = np.sqrt((col - col_search) ** 2. + (row - row_search) ** 2.)
                    computed_distance = True
                    if distance < min_distance:
                        min_distance = distance
                        find_col = col_search
                        find_row = row_search
                        elevation = value
                        break
                row_search = row_search - 1
            # down row process
            row_search = row + 1
            if row_search > (self.rows - 1):
                row_search = self.rows - 1
            while row_search <= (self.rows - 1):
                if computed_distance and abs(row - row_search) > min_distance:
                    break
                if not np.ma.is_masked(data[row_search, col_search]):
                    value = data[row_search, col_search] * self.scale_by_band[0] + self.offset_by_band[0]
                    distance = np.sqrt((col - col_search) ** 2. + (row - row_search) ** 2.)
                    computed_distance = True
                    if distance < min_distance:
                        min_distance = distance
                        find_col = col_search
                        find_row = row_search
                        elevation = value
                        break
                row_search = row_search + 1
            col_search = col_search + 1
        return str_error, elevation

    def get_vector_dem_intersection(self,
                                    source_crs_id,
                                    v_fp,
                                    v_sp):
        is_debugging = True
        str_error = ''
        pto_int = []
        raster_dem_crs_id = self.get_crs_id()
        if isinstance(v_fp, np.ndarray):
            v_fp = v_fp.tolist()
        if isinstance(v_sp, np.ndarray):
            v_sp = v_sp.tolist()
        v_fp_fc = v_fp[0]
        v_fp_sc = v_fp[1]
        v_fp_tc = v_fp[2]
        v_sp_fc = v_sp[0]
        v_sp_sc = v_sp[1]
        v_sp_tc = v_sp[2]
        if raster_dem_crs_id != source_crs_id:
            vector_raster_dem_crs_aux = [[v_fp[0], v_fp[1], v_fp[2]],
                                         [v_sp[0], v_sp[1], v_sp[2]]]
            str_error = self.crs_tools.operation(source_crs_id, raster_dem_crs_id, vector_raster_dem_crs_aux)
            if str_error:
                str_error = ('From CRS: {} to CRS: {}\nError:\n{}'.
                             format(source_crs_id, raster_dem_crs_id, str_error))
                return str_error, pto_int
            v_fp_fc = vector_raster_dem_crs_aux[0][0]
            v_fp_sc = vector_raster_dem_crs_aux[0][1]
            v_fp_tc = vector_raster_dem_crs_aux[0][2]
            v_sp_fc = vector_raster_dem_crs_aux[1][0]
            v_sp_sc = vector_raster_dem_crs_aux[1][1]
            v_sp_tc = vector_raster_dem_crs_aux[1][2]
        if is_debugging:
            fp_wkt = ('POINT({:.3f} {:.3f} {:.3f})'.format(v_fp_fc, v_fp_sc, v_fp_tc))
        str_error, fp_elevation = self.get_elevation(v_fp_fc, v_fp_sc)
        if str_error:
            str_error = ('Getting elevation for first point: [{}, {}]\nError:\n{}'.
                         format(str(v_fp_fc), str(v_fp_sc), str_error))
            return str_error, pto_int
        azimuth = np.arctan2(v_sp_fc - v_fp_fc, v_sp_sc - v_fp_sc)
        if azimuth < 0.0:
            azimuth = azimuth + 2.0 * np.pi
        tolerance = self.grid_size / 2.0
        v_distance_2d = np.sqrt((v_sp_fc - v_fp_fc) ** 2.0 + (v_sp_sc - v_fp_sc) ** 2.0)
        v_slope = (v_sp_tc - v_fp_tc) / v_distance_2d
        min_slope = (fp_elevation - v_fp_tc) / self.grid_size
        if v_slope < min_slope:
            fc = v_fp_fc
            sc = v_fp_sc
            tc = fp_elevation
            pto_int = [fc, sc, tc]
            return str_error, pto_int
        str_error, sp_elevation = self.get_elevation(v_sp_fc, v_sp_sc)
        if str_error:
            str_error = ('Getting elevation for second point: [{}, {}]\nError:\n{}'.
                         format(str(v_fp_fc), str(v_fp_sc), str_error))
            return str_error, pto_int
        if is_debugging:
            sp_wkt = ('POINT({:.3f} {:.3f} {:.3f})'.format(v_sp_fc, v_sp_sc, v_sp_tc))
        previous_elevation = None
        previous_fc = None
        previous_sc = None
        distance = self.grid_size
        max_elevation = self.max_value_by_band[0]
        if v_fp_tc > max_elevation:
            # tan(vSlope)=(mMaxElevation-vFpTc)/distance
            distance = (max_elevation - v_fp_tc) / v_slope # ambos negativos
        control = True
        fc = None
        sc = None
        tc = None
        while control:
            if distance > 106.46:
                yo = 1
            fc = v_fp_fc + distance * np.sin(azimuth)
            sc = v_fp_sc + distance * np.cos(azimuth)
            if fc < self.sw_fc or fc > self.ne_fc or sc < self.sw_sc or sc > self.ne_sc:
                if previous_fc and previous_sc and previous_elevation:
                    fc = previous_fc
                    sc = previous_sc
                    tc = previous_elevation
                    break
            vp_tc = v_fp_tc + distance * v_slope
            str_error, p_elevation = self.get_elevation(fc, sc)
            if str_error:
                str_error = ('Getting elevation for point: [{}, {}]\nError:\n{}'.
                             format(str(fc), str(sc), str_error))
                return str_error, pto_int
            tc = p_elevation
            height_difference = vp_tc - p_elevation
            if is_debugging:
                ip_wkt = ('POINT({:.3f} {:.3f} {:.3f})'.format(fc, sc, tc))
            if np.abs(height_difference) < tolerance or vp_tc < p_elevation:
                break
            else:
                previous_elevation = p_elevation
                previousFc = fc
                previousSc = sc
                distance += self.grid_size
        if is_debugging:
            pto_int_wkt = ('POINT({:.3f} {:.3f} {:.3f})'.format(fc, sc, tc))
        pto_int = [fc, sc, tc]
        return str_error, pto_int

    def set_check_domain(self, check_domain):
        self.check_domain = check_domain
