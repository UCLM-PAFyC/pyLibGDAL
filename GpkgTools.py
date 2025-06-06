# authors:
# David Hernandez Lopez, david.hernandez@uclm.es

import os, sys
from osgeo import gdal, osr, ogr
gdal.UseExceptions()

from . import defs_gdal

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

class GpkgTools(object):
    def __init__(self,
                 crs_tools):
        self.crs_tools = crs_tools


    def create(self,
               file_name,
               layers):
        str_error = ''
        driver = ogr.GetDriverByName("GPKG")
        create_options = ['CRS_WKT_EXTENSION=YES',
                          'METADATA_TABLES=YES']
        ds = None
        try:
            ds = driver.CreateDataSource(file_name)
        except Exception as e:
            str_error = 'GDAL Error: ' + e.args[0]
            return str_error
        for layer_name in layers:
            outLayer = None
            geometry_type = layers[layer_name][defs_gdal.LAYERS_GEOMETRY_TYPE_TAG]
            try:
                outLayer = ds.CreateLayer(layer_name, geom_type = geometry_type )
            except Exception as e:
                str_error = 'GDAL Error: ' + e.args[0]
                return str_error
            for field_name in layers[layer_name][defs_gdal.LAYERS_FIELDS_TAG]:
                field_type = layers[layer_name][defs_gdal.LAYERS_FIELDS_TAG][field_name]
                field = None
                try:
                    field = ogr.FieldDefn(field_name, field_type)
                except Exception as e:
                    str_error = 'GDAL Error: ' + e.args[0]
                    return str_error
                try:
                    outLayer.CreateField(field)
                except Exception as e:
                    str_error = 'GDAL Error: ' + e.args[0]
                    return str_error
        return str_error


    def get_field_values(self,
                         file_name,
                         layer_name,
                         field_name,
                         where_field_names,
                         where_field_values):
        str_error = ''
        value = []
        if not os.path.exists(file_name):
            str_error = ('Not exists file:\n{}'.format(file_name))
            return str_error, value
        if len(where_field_names) > 0:
            if len(where_field_names) != len(where_field_values):
                str_error = ('Different number of where field names and values')
                return str_error, value
        ds = ogr.Open(file_name)
        sql = None
        sql = 'SELECT ' + field_name
        sql += (' FROM ' + layer_name)
        if len(where_field_values) > 0:
            sql += (' WHERE')
            cont = 0
            for where_field_name in where_field_names:
                sql += (' ' + where_field_name + ' = \'' + where_field_values[cont] + '\'')
                cont = cont + 1
        layer = ds.ExecuteSQL(sql)
        for i, feature in enumerate(layer):
            value.append(feature.GetField(0))
        return str_error, value

    def get_fields_values(self,
                          file_name,
                          layer_name,
                          fields_names,
                          no_duplicated = False,
                          sort_by_first_field = True):
        str_error = ''
        values = {}
        for fieldName in fields_names:
            values [fieldName] = []
        if not os.path.exists(file_name):
            str_error = ('Not exists file:\n{}'.format(file_name))
            return str_error, values
        ds = ogr.Open(file_name)
        sql = None
        sql = 'SELECT'
        if no_duplicated:
            sql += ' DISTINCT'
        cont = 0
        for fieldName in fields_names:
            if cont > 0:
                sql += ','
            sql += (' ' +  fieldName)
            cont = cont + 1
        sql += (' FROM ' + layer_name)
        if sort_by_first_field:
            sql += (' ORDER BY ' + fields_names[0])
        layer = ds.ExecuteSQL(sql)
        for i, feature in enumerate(layer):
            for nF in range(len(fields_names)):
                values[fields_names[nF]].append(feature.GetField(nF))
        # ds = None
        return str_error, values

    def get_layers_names(self, file_name):
        str_error = ''
        layer_names = []
        if not os.path.exists(file_name):
            str_error = ('Not exists file:\n{}'.format(file_name))
            return str_error, layer_names
        try:
            layer_names = [l.GetName() for l in ogr.Open(file_name)]
        except Exception as e:
            str_error = 'GDAL Error: ' + gdal.GetLastErrorMsg()
        return str_error, layer_names

    def write(self,
              file_name,
              values):
        str_error = ''
        if not os.path.exists(file_name):
            str_error = ('Not exists file:\n{}'.format(file_name))
            return str_error
        driver = ogr.GetDriverByName("GPKG")
        ds = None
        try:
            ds = driver.Open(file_name, update = 1)
        except Exception as e:
            str_error = 'GDAL Error: ' + e.args[0]
            return str_error
        for layer_name in values:
            layer = None
            try:
                layer = ds.GetLayer(layer_name)
            except Exception as e:
                str_error = 'GDAL Error: ' + e.args[0]
                return str_error
            if not layer:
                str_error = ('Not exists layer: {}\nin file:\n{}'.format(layer_name, file_name))
                return str_error
            for i in range(len(values[layer_name])):
                value = values[layer_name][i]
                if not defs_gdal.LAYERS_FIELDS_TAG in value:
                    str_error = ('No {} in value: {} in layer: {}'.
                                 format(defs_gdal.LAYERS_FIELDS_TAG, str(i+1), layer_name))
                    return str_error
                if not defs_gdal.LAYERS_GEOMETRY_TAG in value:
                    str_error = ('No {} in value: {} in layer: {}'.
                                 format(defs_gdal.LAYERS_GEOMETRY_TAG, str(i+1), layer_name))
                    return str_error
                geometry = value[defs_gdal.LAYERS_GEOMETRY_TAG]
                feature = ogr.Feature(layer.GetLayerDefn())  # instantiate OGRFeature
                if geometry:
                    try:
                        feature.SetGeometry(geometry)
                    except Exception as e:
                        str_error = 'GDAL Error: ' + e.args[0]
                        return str_error
                fields = value[defs_gdal.LAYERS_FIELDS_TAG]
                for field in fields:
                    if not defs_gdal.FIELD_NAME_TAG in field:
                        str_error = ('No {} in value: {} in layer: {}'.
                                     format(defs_gdal.FIELD_NAME_TAG, str(i+1), layer_name))
                        return str_error
                    field_name = field[defs_gdal.FIELD_NAME_TAG]
                    if not defs_gdal.FIELD_TYPE_TAG in field:
                        str_error = ('No {} in value: {} in layer: {}'.
                                     format(defs_gdal.FIELD_TYPE_TAG, str(i+1), layer_name))
                        return str_error
                    field_type = field[defs_gdal.FIELD_TYPE_TAG]
                    if not defs_gdal.FIELD_VALUE_TAG in field:
                        str_error = ('No {} in value: {} in layer: {}'.
                                     format(defs_gdal.FIELD_VALUE_TAG, str(i+1), layer_name))
                        return str_error
                    field_value = field[defs_gdal.FIELD_VALUE_TAG]
                    field_idx = layer.GetLayerDefn().GetFieldIndex(field_name)
                    if field_idx == -1:
                        str_error = ('No field: {} in layer: {}\nin file: {}'.
                                     format(field_name, layer_name, file_name))
                        return str_error
                    field_defn = layer.GetLayerDefn().GetFieldDefn(field_idx)
                    field_defn_type = field_defn.GetType()
                    if field_defn_type != field_type:
                        str_error = ('Different type in field: {} in value: {} in layer: {}'.
                                     format(field_name, str(i+1), layer_name))
                        return str_error
                    try:
                        feature.SetField(field_name, field_value)
                    except Exception as e:
                        str_error = 'GDAL Error: ' + e.args[0]
                        return str_error
                try:
                    if layer.CreateFeature(feature) != ogr.OGRERR_NONE:
                        str_error = ('Error writting feature: {}\nin layer: {}\nin file:\n{}'.
                                     format(str(i+1), layer_name, file_name))
                        return str_error
                except Exception as e:
                    str_error = 'GDAL Error: ' + e.args[0]
                    return str_error
        return str_error