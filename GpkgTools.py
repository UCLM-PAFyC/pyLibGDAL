# authors:
# David Hernandez Lopez, david.hernandez@uclm.es

import os, sys
from osgeo import gdal, osr, ogr
gdal.UseExceptions()

from . import defs_gdal

class GpkgTools(object):
    def __init__(self,
                 crs_tools):
        self.crs_tools = crs_tools

    def create(self,
               file_name,
               layers,
               layers_crs_id,
               ignore_existing_layers,
               create_options = None):
        str_error = ''
        if not isinstance(layers, dict):
            str_error = ('Fields argument must be a dictionary of dictionary: \'layer name\': \'fields\'')
            return str_error
        if not isinstance(layers_crs_id, dict):
            str_error = ('Layers CRS Id argument must be a dictionary of dictionary: \'layer name\': \'crs_id\'')
            return str_error
        for layer_name in layers:
            if not isinstance(layers[layer_name], dict):
                str_error = ('Fields argument must be a dictionary of dictionary: \'layer name\': \'fields\'')
                return str_error
            if not defs_gdal.LAYERS_GEOMETRY_TAG in layers[layer_name]:
                str_error = ('All layers must has a geometry field, type none for no geometry')
                return str_error
            # if not layers[layer_name][defs_gdal.LAYERS_GEOMETRY_TAG] in defs_gdal.geometry_type_by_name:
            if not layers[layer_name][defs_gdal.LAYERS_GEOMETRY_TAG] in defs_gdal.geometry_name_by_type:
                str_error = ('All layers must has a valid geometry field, type none for no geometry')
                return str_error
            if not layer_name in layers_crs_id:
                str_error = ('All layers must has a CRS Id, in layers CRS id argument')
                return str_error
        driver = ogr.GetDriverByName("GPKG")
        ds = None
        try:
            if not ignore_existing_layers:
                if create_options:
                    ds = driver.CreateDataSource(file_name, create_options)
                else:
                    ds = driver.CreateDataSource(file_name)
            else:
                ds = driver.Open(file_name, update=1)
        except Exception as e:
            str_error = 'GDAL Error: ' + e.args[0]
            return str_error
        for layer_name in layers:
            current_layer = None
            try:
                current_layer = ds.GetLayer(layer_name)
            except Exception as e:
                str_error = 'GDAL Error: ' + e.args[0]
                return str_error
            if current_layer:
                if ignore_existing_layers:
                    continue
                else:
                    # to do, remove?
                    yo = 1
            outLayer = None
            geometry_type = layers[layer_name][defs_gdal.LAYERS_GEOMETRY_TAG]
            crs_id = layers_crs_id[layer_name]
            crs = None
            if crs_id:
                crs = osr.SpatialReference()
                try:
                    crs.SetFromUserInput(crs_id)
                except Exception as e:
                    str_error = 'GDAL Error: ' + e.args[0]
                    return str_error
            try:
                if crs:
                    outLayer = ds.CreateLayer(layer_name, crs, geom_type = geometry_type )
                else:
                    outLayer = ds.CreateLayer(layer_name, crs, geom_type = geometry_type )
            except Exception as e:
                str_error = 'GDAL Error: ' + e.args[0]
                return str_error
            for field_name in layers[layer_name]:
                if field_name == defs_gdal.LAYERS_GEOMETRY_TAG:
                    continue
                field_type = layers[layer_name][field_name]
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

    def get_features(self,
                     file_name,
                     layer_name,
                     fields,
                     filter_fields_or_string= None):
        str_error = ''
        features = []
        if not os.path.exists(file_name):
            str_error = ('Not exists file:\n{}'.format(file_name))
            return str_error, features
        if not isinstance(fields, dict):
            str_error = ('Fields argument must be a dictionary: \'field name\': \'field type\'')
            return str_error, features
        if filter_fields_or_string:
            if not isinstance(filter_fields_or_string, str):
                if not isinstance(filter_fields_or_string, dict):
                    str_error = ('Filter fields argument must be a dictionary: \'field name\': \'field type\'')
                    return str_error, features
        ds = None
        try:
            ds = ogr.Open(file_name)
        except Exception as e:
            str_error = 'GDAL Error: ' + e.args[0]
            return str_error, features
        layer = None
        try:
            layer = ds.GetLayer(layer_name)
        except Exception as e:
            str_error = 'GDAL Error: ' + e.args[0]
            return str_error, features
        if not layer:
            str_error = ('Not exists layer: {}\nin file:\n{}'.format(layer_name, file_name))
            return str_error, features
        for field_name in fields:
            field_type = fields[field_name]
            if field_name == defs_gdal.LAYERS_GEOMETRY_TAG:
                if field_type != layer.GetGeomType():
                    str_error = ('In file:\n{}\nin layer: {}\ngeometry type is: {}\ndifferent for selected: {}'.
                                 format(file_name, layer_name, ogr.GeometryTypeToName(layer.GetGeomType()),
                                        ogr.GeometryTypeToName(field_type)))
                    return str_error, features
                continue
            field_idx = layer.GetLayerDefn().GetFieldIndex(field_name)
            if field_idx == -1:
                str_error = ('No field: {} in layer: {}\nin file: {}'.
                             format(field_name, layer_name, file_name))
                return str_error, features
            field_defn = layer.GetLayerDefn().GetFieldDefn(field_idx)
            field_defn_type = field_defn.GetType()
            if field_defn_type != field_type:
                str_error = ('Different type in field: {} in value: {} in layer: {}\nin file:\n{}'.
                             format(field_name, str(i + 1), layer_name, file_name))
                return str_error, features
        if filter_fields_or_string:
            filter_str = ''
            if not isinstance(filter_fields_or_string, str):
                cont_filter_field = 0
                for filter_field_name in filter_fields_or_string:
                    filter_field_value = filter_fields_or_string[filter_field_name]
                    if filter_field_name == defs_gdal.LAYERS_GEOMETRY_TAG:
                        # to do
                        # if field_type != layer.GetGeomType():
                        #     str_error = ('In file:\n{}\nin layer: {}\ngeometry type is: {}\ndifferent for selected: {}'.
                        #                  format(file_name, layer_name, ogr.GeometryTypeToName(layer.GetGeomType()),
                        #                         ogr.GeometryTypeToName(field_type)))
                        #     return str_error, features
                        continue
                    filter_field_idx = layer.GetLayerDefn().GetFieldIndex(filter_field_name)
                    if filter_field_idx == -1:
                        str_error = ('No field: {} in layer: {}\nin file: {}'.
                                     format(filter_field_name, layer_name, file_name))
                        return str_error, features
                    filter_field_defn = layer.GetLayerDefn().GetFieldDefn(filter_field_idx)
                    filter_field_defn_type = filter_field_defn.GetType()
                    if cont_filter_field > 0:
                        filter_str += ' and '
                    filter_str += filter_field_name
                    filter_str += ' = '
                    if filter_field_defn_type == ogr.OFTString:
                        filter_str += '\''
                    filter_str += str(filter_field_value)
                    if filter_field_defn_type == ogr.OFTString:
                        filter_str += '\''
                    cont_filter_field = cont_filter_field + 1
            else:
                filter_str = filter_fields_or_string
            layer.SetAttributeFilter(filter_str)
        layer.ResetReading()
        cont_feature = 0
        # # debug: checking filter
        # number_of_features = layer.GetFeatureCount()
        for feature in layer:
            feature_fields = {}
            for field_name in fields:
                field_type = fields[field_name]
                if field_name == defs_gdal.LAYERS_GEOMETRY_TAG:
                    feature_fields[field_name] = feature.GetGeometryRef().ExportToWkb()
                    continue
                field_idx = layer.GetLayerDefn().GetFieldIndex(field_name)
                value = None
                if field_type == defs_gdal.type_by_name['string']:
                    value = feature.GetFieldAsString(field_idx)
                elif field_type == defs_gdal.type_by_name['real']:
                    value = feature.GetFieldAsDouble(field_idx)
                elif field_type == defs_gdal.type_by_name['int']:
                    value = feature.GetFieldAsInteger(field_idx)
                feature_fields[field_name] = value
            features.append(feature_fields)
            cont_feature = cont_feature + 1
        if filter_fields_or_string:
            layer.SetAttributeFilter("")
            # # debug: checking filter
            # layer.ResetReading()
            # number_of_features = layer.GetFeatureCount()
            # yo = 1
        return str_error, features

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

    def remove(self,
               file_name,
               features_filter_fields_by_layer):
        # if there are several features for filter all of them will be uptated
        str_error = ''
        if not os.path.exists(file_name):
            str_error = ('Not exists file:\n{}'.format(file_name))
            return str_error
        if not isinstance(features_filter_fields_by_layer, dict):
            str_error = ('Features filters by layer argument must be a dictionary of lists')
            return str_error
        for layer_name in features_filter_fields_by_layer:
            if not isinstance(features_filter_fields_by_layer[layer_name], list):
                str_error = ('Features filters by layer argument must be a dictionary of lists')
                return str_error
        driver = ogr.GetDriverByName("GPKG")
        ds = None
        try:
            ds = driver.Open(file_name, update = 1)
        except Exception as e:
            str_error = 'GDAL Error: ' + e.args[0]
            return str_error
        for layer_name in features_filter_fields_by_layer:
            layer = None
            try:
                layer = ds.GetLayer(layer_name)
            except Exception as e:
                str_error = 'GDAL Error: ' + e.args[0]
                return str_error
            if not layer:
                str_error = ('Not exists layer: {}\nin file:\n{}'.format(layer_name, file_name))
                return str_error
            for i in range(len(features_filter_fields_by_layer[layer_name])):
                feature_filter_fields = features_filter_fields_by_layer[layer_name][i]
                cont_filter_field = 0
                filter_str = ""
                for filter_field_pos in range(len(feature_filter_fields)):
                    filter_field = feature_filter_fields[filter_field_pos]
                    if not isinstance(filter_field, dict):
                        str_error = ('In layer: {}, feature filter: {}, field: {} is not a dictionary'
                                     .format(layer_name, str(i + 1), str(filter_field_pos + 1)))
                        return str_error
                    if not defs_gdal.FIELD_NAME_TAG in filter_field:
                        str_error = ('In layer: {}, feature: {}, filter field: {} not contains: {}'
                                     .format(layer_name, str(i + 1), str(filter_field_pos), defs_gdal.FIELD_NAME_TAG))
                        return str_error
                    filter_field_name = filter_field[defs_gdal.FIELD_NAME_TAG]
                    if filter_field_name == defs_gdal.LAYERS_GEOMETRY_TAG:
                        # to do
                        continue
                    filter_field_idx = layer.GetLayerDefn().GetFieldIndex(filter_field_name)
                    if filter_field_idx == -1:
                        str_error = ('No filter field: {} in layer: {}\nin file: {}'.
                                     format(filter_name, layer_name, file_name))
                        return str_error
                    if not defs_gdal.FIELD_TYPE_TAG in filter_field:
                        str_error = ('In layer: {}, feature: {}, filter field: {} not contains: {}'
                                     .format(layer_name, str(i + 1), str(filter_field_pos + 1), defs_gdal.FIELD_NAME_TAG))
                        return str_error
                    if not defs_gdal.FIELD_VALUE_TAG in filter_field:
                        str_error = ('In layer: {}, feature: {}, filter field: {} not contains: {}'
                                     .format(layer_name, str(i + 1), str(filter_field_pos + 1), defs_gdal.FIELD_VALUE_TAG))
                        return str_error
                    filter_field_type = filter_field[defs_gdal.FIELD_TYPE_TAG]
                    filter_field_defn = layer.GetLayerDefn().GetFieldDefn(filter_field_idx)
                    filter_field_defn_type = filter_field_defn.GetType()
                    if filter_field_defn_type != filter_field_type:
                        str_error = ('Different type in filter field: {} in value: {} in layer: {}\nin file:\n{}'.
                                     format(filter_field_name, str(i + 1), layer_name, file_name))
                        return str_error
                    filter_field_value = filter_field[defs_gdal.FIELD_VALUE_TAG]
                    if cont_filter_field > 0:
                        filter_str += ' and '
                    filter_str += filter_field_name
                    filter_str += ' = '
                    if filter_field_defn_type == ogr.OFTString:
                        filter_str += '\''
                    filter_str += str(filter_field_value)
                    if filter_field_defn_type == ogr.OFTString:
                        filter_str += '\''
                    cont_filter_field = cont_filter_field + 1
                layer.SetAttributeFilter(filter_str)
                layer.ResetReading()
                cont_feature = 0
                number_of_features = layer.GetFeatureCount() # must be one if only one feature for filters
                for feature in layer:
                    try:
                        layer.DeleteFeature(feature.GetFID())
                    except Exception as e:
                        str_error = 'GDAL Error: ' + e.args[0]
                        return str_error
            ds.FlushCache()
            # try:
            #     str_sql = 'REPACK ' + layer_name
            #     ds.ExecuteSQL(str_sql)
            # except Exception as e:
            #     str_error = 'GDAL Error: ' + e.args[0]
            #     return str_error
        return str_error

    def update(self,
               file_name,
               features_by_layer,
               features_filter_fields_by_layer):
        # if there are several features for filter all of them will be uptated
        str_error = ''
        if not os.path.exists(file_name):
            str_error = ('Not exists file:\n{}'.format(file_name))
            return str_error
        if not isinstance(features_by_layer, dict):
            str_error = ('Features by layer argument must be a dictionary of lists')
            return str_error
        for layer_name in features_by_layer:
            if not isinstance(features_by_layer[layer_name], list):
                str_error = ('Features by layer argument must be a dictionary of lists')
                return str_error
        if not isinstance(features_filter_fields_by_layer, dict):
            str_error = ('Features filters by layer argument must be a dictionary of lists')
            return str_error
        for layer_name in features_filter_fields_by_layer:
            if not isinstance(features_filter_fields_by_layer[layer_name], list):
                str_error = ('Features filters by layer argument must be a dictionary of lists')
                return str_error
        driver = ogr.GetDriverByName("GPKG")
        ds = None
        try:
            ds = driver.Open(file_name, update = 1)
        except Exception as e:
            str_error = 'GDAL Error: ' + e.args[0]
            return str_error
        for layer_name in features_by_layer:
            if not layer_name in features_filter_fields_by_layer:
                str_error = ('There are no features filters for layer: {}'.format(layer_name))
                return str_error
            if len(features_by_layer[layer_name]) != len(features_filter_fields_by_layer[layer_name]):
                str_error = ('Different number of features in filters for layer: {}\n'.format(layer_name))
                return str_error
            layer = None
            try:
                layer = ds.GetLayer(layer_name)
            except Exception as e:
                str_error = 'GDAL Error: ' + e.args[0]
                return str_error
            if not layer:
                str_error = ('Not exists layer: {}\nin file:\n{}'.format(layer_name, file_name))
                return str_error
            for i in range(len(features_by_layer[layer_name])):
                if not isinstance(features_by_layer[layer_name][i], list):
                    str_error = ('In layer: {}, feature: {} is not a list'.format(layer_name, str(i+1)))
                    return str_error
                feature_filter_fields = features_filter_fields_by_layer[layer_name][i]
                cont_filter_field = 0
                filter_str = ""
                for filter_field_pos in range(len(feature_filter_fields)):
                    filter_field = feature_filter_fields[filter_field_pos]
                    if not isinstance(filter_field, dict):
                        str_error = ('In layer: {}, feature filter: {}, field: {} is not a dictionary'
                                     .format(layer_name, str(i + 1), str(filter_field_pos + 1)))
                        return str_error
                    if not defs_gdal.FIELD_NAME_TAG in filter_field:
                        str_error = ('In layer: {}, feature: {}, filter field: {} not contains: {}'
                                     .format(layer_name, str(i + 1), str(filter_field_pos), defs_gdal.FIELD_NAME_TAG))
                        return str_error
                    filter_field_name = filter_field[defs_gdal.FIELD_NAME_TAG]
                    if filter_field_name == defs_gdal.LAYERS_GEOMETRY_TAG:
                        # to do
                        continue
                    filter_field_idx = layer.GetLayerDefn().GetFieldIndex(filter_field_name)
                    if filter_field_idx == -1:
                        str_error = ('No filter field: {} in layer: {}\nin file: {}'.
                                     format(filter_name, layer_name, file_name))
                        return str_error
                    if not defs_gdal.FIELD_TYPE_TAG in filter_field:
                        str_error = ('In layer: {}, feature: {}, filter field: {} not contains: {}'
                                     .format(layer_name, str(i + 1), str(filter_field_pos + 1), defs_gdal.FIELD_NAME_TAG))
                        return str_error
                    if not defs_gdal.FIELD_VALUE_TAG in filter_field:
                        str_error = ('In layer: {}, feature: {}, filter field: {} not contains: {}'
                                     .format(layer_name, str(i + 1), str(filter_field_pos + 1), defs_gdal.FIELD_VALUE_TAG))
                        return str_error
                    filter_field_type = filter_field[defs_gdal.FIELD_TYPE_TAG]
                    filter_field_defn = layer.GetLayerDefn().GetFieldDefn(filter_field_idx)
                    filter_field_defn_type = filter_field_defn.GetType()
                    if filter_field_defn_type != filter_field_type:
                        str_error = ('Different type in filter field: {} in value: {} in layer: {}\nin file:\n{}'.
                                     format(filter_field_name, str(i + 1), layer_name, file_name))
                        return str_error
                    filter_field_value = filter_field[defs_gdal.FIELD_VALUE_TAG]
                    if cont_filter_field > 0:
                        filter_str += ' and '
                    filter_str += filter_field_name
                    filter_str += ' = '
                    if filter_field_defn_type == ogr.OFTString:
                        filter_str += '\''
                    filter_str += str(filter_field_value)
                    if filter_field_defn_type == ogr.OFTString:
                        filter_str += '\''
                    cont_filter_field = cont_filter_field + 1
                layer.SetAttributeFilter(filter_str)
                layer.ResetReading()
                cont_feature = 0
                number_of_features = layer.GetFeatureCount() # must be one if only one feature for filters
                for feature in layer:
                    feature_fields = features_by_layer[layer_name][i]
                    find_geometry_field = False
                    for field_pos in range(len(feature_fields)):
                        field = feature_fields[field_pos]
                        if not isinstance(field, dict):
                            str_error = ('In layer: {}, feature: {}, field: {} is not a dictionary'
                                         .format(layer_name, str(i + 1), str(field_pos + 1)))
                            return str_error
                        if not defs_gdal.FIELD_NAME_TAG in field:
                            str_error = ('In layer: {}, feature: {}, field: {} not contains: {}'
                                         .format(layer_name, str(i + 1), str(field_pos + 1), defs_gdal.FIELD_NAME_TAG))
                            return str_error
                        field_name = field[defs_gdal.FIELD_NAME_TAG]
                        if field_name == defs_gdal.LAYERS_GEOMETRY_TAG:
                            find_geometry_field = True
                            wkb_geometry = field[defs_gdal.FIELD_VALUE_TAG]
                            if wkb_geometry != defs_gdal.geometry_type_by_name['none']:
                                geometry = None
                                try:
                                    geometry = ogr.CreateGeometryFromWkb(wkb_geometry)
                                except Exception as e:
                                    str_error = 'GDAL Error: ' + e.args[0]
                                    return str_error
                                try:
                                    feature.SetGeometry(geometry)
                                except Exception as e:
                                    str_error = 'GDAL Error: ' + e.args[0]
                                    return str_error
                            continue
                        field_idx = layer.GetLayerDefn().GetFieldIndex(field_name)
                        if field_idx == -1:
                            str_error = ('No field: {} in layer: {}\nin file: {}'.
                                         format(field_name, layer_name, file_name))
                            return str_error
                        if not defs_gdal.FIELD_TYPE_TAG in field:
                            str_error = ('In layer: {}, feature: {}, field: {} not contains: {}'
                                         .format(layer_name, str(i + 1), str(field_pos + 1), defs_gdal.FIELD_NAME_TAG))
                            return str_error
                        if not defs_gdal.FIELD_VALUE_TAG in field:
                            str_error = ('In layer: {}, feature: {}, field: {} not contains: {}'
                                         .format(layer_name, str(i + 1), str(field_pos + 1), defs_gdal.FIELD_VALUE_TAG))
                            return str_error
                        field_type = field[defs_gdal.FIELD_TYPE_TAG]
                        field_value = field[defs_gdal.FIELD_VALUE_TAG]
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
                    # if not find_geometry_field:
                    #     str_error = ('In layer: {}, feature: {}, not contains geometry field'
                    #                  .format(layer_name, str(i + 1)))
                    #     return str_error
                    try:
                        if layer.SetFeature(feature) != ogr.OGRERR_NONE:
                            str_error = ('Error updating feature: {}\nin layer: {}\nin file:\n{}'.
                                         format(str(i+1), layer_name, file_name))
                            return str_error
                    except Exception as e:
                        str_error = 'GDAL Error: ' + e.args[0]
                        return str_error
        return str_error

    def write(self,
              file_name,
              features_by_layer):
        str_error = ''
        if not os.path.exists(file_name):
            str_error = ('Not exists file:\n{}'.format(file_name))
            return str_error
        if not isinstance(features_by_layer, dict):
            str_error = ('Features by layer argument must be a dictionary of lists')
            return str_error
        for layer_name in features_by_layer:
            if not isinstance(features_by_layer[layer_name], list):
                str_error = ('Features by layer argument must be a dictionary of lists')
                return str_error
        driver = ogr.GetDriverByName("GPKG")
        ds = None
        try:
            ds = driver.Open(file_name, update = 1)
        except Exception as e:
            str_error = 'GDAL Error: ' + e.args[0]
            return str_error
        for layer_name in features_by_layer:
            layer = None
            try:
                layer = ds.GetLayer(layer_name)
            except Exception as e:
                str_error = 'GDAL Error: ' + e.args[0]
                return str_error
            if not layer:
                str_error = ('Not exists layer: {}\nin file:\n{}'.format(layer_name, file_name))
                return str_error
            for i in range(len(features_by_layer[layer_name])):
                if not isinstance(features_by_layer[layer_name][i], list):
                    str_error = ('In layer: {}, feature: {} is not a list'.format(layer_name, str(i+1)))
                    return str_error
                feature_fields = features_by_layer[layer_name][i]
                find_geometry_field = False
                feature = ogr.Feature(layer.GetLayerDefn())  # instantiate OGRFeature
                for field_pos in range(len(feature_fields)):
                    field = feature_fields[field_pos]
                    if not isinstance(field, dict):
                        str_error = ('In layer: {}, feature: {}, field: {} is not a dictionary'
                                     .format(layer_name, str(i + 1), str(field_pos)))
                        return str_error
                    if not defs_gdal.FIELD_NAME_TAG in field:
                        str_error = ('In layer: {}, feature: {}, field: {} not contains: {}'
                                     .format(layer_name, str(i + 1), str(field_pos), defs_gdal.FIELD_NAME_TAG))
                        return str_error
                    field_name = field[defs_gdal.FIELD_NAME_TAG]
                    if field_name == defs_gdal.LAYERS_GEOMETRY_TAG:
                        find_geometry_field = True
                        wkb_geometry = field[defs_gdal.FIELD_VALUE_TAG]
                        if wkb_geometry != defs_gdal.geometry_type_by_name['none']:
                            geometry = None
                            try:
                                geometry = ogr.CreateGeometryFromWkb(wkb_geometry)
                            except Exception as e:
                                str_error = 'GDAL Error: ' + e.args[0]
                                return str_error
                            try:
                                # wkt = geometry.ExportToWkt()
                                feature.SetGeometry(geometry)
                                # feature_geometry = feature.GetGeometryRef()
                                # feature_wkt = feature_geometry.ExportToWkt()
                                # yo = 1
                            except Exception as e:
                                str_error = 'GDAL Error: ' + e.args[0]
                                return str_error
                        continue
                    field_idx = layer.GetLayerDefn().GetFieldIndex(field_name)
                    if field_idx == -1:
                        str_error = ('No field: {} in layer: {}\nin file: {}'.
                                     format(field_name, layer_name, file_name))
                        return str_error
                    if not defs_gdal.FIELD_TYPE_TAG in field:
                        str_error = ('In layer: {}, feature: {}, field: {} not contains: {}'
                                     .format(layer_name, str(i + 1), str(field_pos), defs_gdal.FIELD_NAME_TAG))
                        return str_error
                    if not defs_gdal.FIELD_VALUE_TAG in field:
                        str_error = ('In layer: {}, feature: {}, field: {} not contains: {}'
                                     .format(layer_name, str(i + 1), str(field_pos), defs_gdal.FIELD_VALUE_TAG))
                        return str_error
                    field_type = field[defs_gdal.FIELD_TYPE_TAG]
                    field_value = field[defs_gdal.FIELD_VALUE_TAG]
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
                if not find_geometry_field:
                    str_error = ('In layer: {}, feature: {}, not contains geometry field'
                                 .format(layer_name, str(i + 1)))
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