# authors:
# David Hernandez Lopez, david.hernandez@uclm.es

import os, sys
from osgeo import gdal, osr, ogr

current_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(current_path, '..'))

from pyLibGDAL import defs_gdal
from pyLibCRSs import CRSsDefines as defs_crs
from pyLibCRSs.CRSsTools import CRSsTools

class PostGISTools(object):
    @classmethod
    def get_sql_create_spatial_table(self,
                                     layers,
                                     layers_crs_id,
                                     restrictions_in_fields_by_layer,
                                     db_schema = None):
        str_error = ''
        sqls = []
        if not db_schema is None:
            if not isinstance(db_schema, str):
                str_error = ('db_schema must be a string')
                return str_error, sqls
        for layer_name in layers:
            if not isinstance(layers[layer_name], dict):
                str_error = ('Fields argument must be a dictionary of dictionary: \'layer name\': \'fields\'')
                return str_error, sqls
            if not defs_gdal.LAYERS_GEOMETRY_POSTGIS_TAG in layers[layer_name]:
                str_error = ('All layers must has a geometry field, type none for no geometry')
                return str_error, sqls
            # if not layers[layer_name][defs_gdal.LAYERS_GEOMETRY_TAG] in defs_gdal.geometry_type_by_name:
            if not layers[layer_name][defs_gdal.LAYERS_GEOMETRY_POSTGIS_TAG] in defs_gdal.geometry_name_by_type:
                str_error = ('All layers must has a valid geometry field, type none for no geometry')
                return str_error, sqls
            if not layer_name in layers_crs_id:
                str_error = ('All layers must has a CRS Id, in layers CRS id argument')
                return str_error, sqls
        postgis_geometry_type = None
        for layer_name in layers:
            geometry_type = layers[layer_name][defs_gdal.LAYERS_GEOMETRY_POSTGIS_TAG]
            if not geometry_type in defs_gdal.postgis_geometry_type_by_ogr_type:
                str_error = ('Not exists postgis geometry type for GDAL geometry type: {}'.format(str(geometry_type)))
                return str_error, sqls
            postgis_geometry_type = defs_gdal.postgis_geometry_type_by_ogr_type[geometry_type]
            crs_id = layers_crs_id[layer_name]
            crs = None
            srs_id = None
            if crs_id:
                crs = osr.SpatialReference()
                try:
                    crs.SetFromUserInput(crs_id)
                except Exception as e:
                    str_error = 'GDAL Error: ' + e.args[0]
                    return str_error
                srs_id = crs_id.replace(defs_crs.EPSG_STRING_PREFIX, ' ')
                if '+' in srs_id:
                    srs_id = srs_id.replace('+', ' ')
                    srs_id = srs_id.strip()
                    values = srs_id.split(' ')
                    srs_id = values[0]
            sql = ''
            if db_schema is None:
                sql = ('CREATE TABLE {} ('.format(layer_name))
            else:
                sql = ('CREATE TABLE {}.{} ('.format(db_schema, layer_name))
            sql += ('{} BIGSERIAL PRIMARY KEY'.format(defs_gdal.POSTGIS_FIELD_FID_NAME))#INTEGER NOT NULL PRIMARY KEY'
            # sql += 'gid INTEGER NOT NULL PRIMARY KEY'
            for field_name in layers[layer_name]:
                if field_name == defs_gdal.LAYERS_GEOMETRY_POSTGIS_TAG:
                    continue
                field_type = layers[layer_name][field_name]
                field_type = defs_gdal.postgis_type_by_ogr_type[field_type]
                sql += (',{} {}'.format(field_name, field_type))
                if layer_name in restrictions_in_fields_by_layer:
                    if field_name in restrictions_in_fields_by_layer[layer_name]:
                        for restriction in restrictions_in_fields_by_layer[layer_name][field_name]:
                            sql += (' {}'.format(restriction))
            sql += ')'
            sqls.append(sql)
            if geometry_type != defs_gdal.geometry_type_by_name['none']:
                # SELECT AddGeometryColumn('terrain_points', 'wkb_geometry', 3725, 'POINT', 3 );
                if db_schema is None:
                    sql = ('SELECT AddGeometryColumn(\'{}\',\'{}\',{},\'{}\',2)'
                           .format(layer_name, defs_gdal.LAYERS_GEOMETRY_POSTGIS_TAG,
                                   srs_id, postgis_geometry_type))
                else:
                    sql = ('SELECT AddGeometryColumn(\'{}\',\'{}\',\'{}\',{},\'{}\',2)'
                           .format(db_schema,layer_name, defs_gdal.LAYERS_GEOMETRY_POSTGIS_TAG,
                                   srs_id, postgis_geometry_type))
                sqls.append(sql)
        return str_error, sqls

    @classmethod
    def get_sql_delete_features(self,
                                features_filter_fields_by_layer= None,
                                db_schema = None):
        str_error = ''
        sqls = []
        if not db_schema is None:
            if not isinstance(db_schema, str):
                str_error = ('db_schema must be a string')
                return str_error, sqls
        if not isinstance(features_filter_fields_by_layer, dict):
            str_error = ('Features filters by layer argument must be a dictionary of lists')
            return str_error
        for layer_name in features_filter_fields_by_layer:
            if not isinstance(features_filter_fields_by_layer[layer_name], list):
                str_error = ('Features filters by layer argument must be a dictionary of lists')
                return str_error
        for layer_name in features_filter_fields_by_layer:
            for i in range(len(features_filter_fields_by_layer[layer_name])):
                feature_filter_fields = features_filter_fields_by_layer[layer_name][i]
                cont_filter_field = 0
                sql = ''
                if db_schema is None:
                    sql = ('DELETE FROM {} WHERE '.format(layer_name))
                else:
                    sql = ('DELETE FROM {}.{} WHERE '.format(db_schema, layer_name))
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
                    if (filter_field_name == defs_gdal.LAYERS_GEOMETRY_TAG
                            or filter_field_name == defs_gdal.LAYERS_GEOMETRY_POSTGIS_TAG):
                        # to do
                        continue
                    if not defs_gdal.FIELD_TYPE_TAG in filter_field:
                        str_error = ('In layer: {}, feature: {}, filter field: {} not contains: {}'
                                     .format(layer_name, str(i + 1), str(filter_field_pos + 1), defs_gdal.FIELD_NAME_TAG))
                        return str_error
                    if not defs_gdal.FIELD_VALUE_TAG in filter_field:
                        str_error = ('In layer: {}, feature: {}, filter field: {} not contains: {}'
                                     .format(layer_name, str(i + 1), str(filter_field_pos + 1), defs_gdal.FIELD_VALUE_TAG))
                        return str_error
                    filter_field_type = filter_field[defs_gdal.FIELD_TYPE_TAG]
                    filter_field_value = filter_field[defs_gdal.FIELD_VALUE_TAG]
                    if cont_filter_field > 0:
                        filter_str += ' AND '
                    filter_str += filter_field_name
                    filter_str += ' = '
                    if defs_gdal.name_by_type[filter_field_type] == 'string':
                        filter_str += '\''
                    filter_str += str(filter_field_value)
                    if defs_gdal.name_by_type[filter_field_type] == 'string':
                        filter_str += '\''
                    cont_filter_field = cont_filter_field + 1
                sql += filter_str
                # sql += ';'
                sqls.append(sql)
        return str_error, sqls

    @classmethod
    def get_sql_get_features(self,
                             layer_name,
                             fields,
                             filter_fields_or_string= None,
                             db_schema = None):
        str_error = ''
        sqls = []
        if not db_schema is None:
            if not isinstance(db_schema, str):
                str_error = ('db_schema must be a string')
                return str_error, sqls
        if not isinstance(layer_name, str):
            str_error = ('layer_name must be a string')
            return str_error, sqls
        if not isinstance(fields, dict):
            str_error = ('Fields argument must be a dictionary: \'field name\': \'field type\'')
            return str_error, features
        if filter_fields_or_string:
            if not isinstance(filter_fields_or_string, str):
                if not isinstance(filter_fields_or_string, dict):
                    str_error = ('Filter fields argument must be a dictionary: \'field name\': \'field type\'')
                    return str_error, features
        sql = 'SELECT '
        number_of_inserted_fields = 0
        for field_name in fields:
            field_type = fields[field_name]
            if (field_name == defs_gdal.LAYERS_GEOMETRY_TAG
                    or field_name == defs_gdal.LAYERS_GEOMETRY_POSTGIS_TAG):
                if field_type == defs_gdal.geometry_type_by_name['none']:
                    continue
            # if ignore_geometry:
            #     if (field_name == defs_gdal.LAYERS_GEOMETRY_TAG
            #             or field_name == defs_gdal.LAYERS_GEOMETRY_POSTGIS_TAG):
            #         if field_type == defs_gdal.geometry_type_by_name['none']:
            #             continue
            if number_of_inserted_fields > 0:
                sql += ','
            sql += field_name
            number_of_inserted_fields += 1
        if db_schema is None:
            sql += ' FROM {} '.format(layer_name)
        else:
            sql += ' FROM {}.{} '.format(db_schema, layer_name)
        if not filter_fields_or_string is None:
            sql += ' WHERE '
            number_of_inserted_fields = 0
            for filter_field_name in filter_fields_or_string:
                filter_field_value = filter_fields_or_string[filter_field_name]
                if number_of_inserted_fields > 0:
                    sql += ','
                sql += filter_field_name
                sql += ' = '
                if isinstance(filter_field_value, str):
                    sql += ('\'{}\''.format(filter_field_value))
                else:
                    sql += str(filter_field_value)
                number_of_inserted_fields += 1
        # sql += ';'
        sqls.append(sql)
        return str_error, sqls

    @classmethod
    def get_sql_update_features(self,
                                features_by_layer,
                                features_filter_fields_by_layer,
                                db_schema = None):
        str_error = ''
        sqls = []
        if not db_schema is None:
            if not isinstance(db_schema, str):
                str_error = ('db_schema must be a string')
                return str_error, sqls
        if not isinstance(features_by_layer, dict):
            str_error = ('Features by layer argument must be a dictionary of lists')
            return str_error, sqls
        for layer_name in features_by_layer:
            if not isinstance(features_by_layer[layer_name], list):
                str_error = ('Features by layer argument must be a dictionary of lists')
                return str_error, sqls
        if not isinstance(features_filter_fields_by_layer, dict):
            str_error = ('Features filters by layer argument must be a dictionary of lists')
            return str_error, sqls
        for layer_name in features_filter_fields_by_layer:
            if not isinstance(features_filter_fields_by_layer[layer_name], list):
                str_error = ('Features filters by layer argument must be a dictionary of lists')
                return str_error, sqls
        for layer_name in features_by_layer:
            if not layer_name in features_filter_fields_by_layer:
                str_error = ('There are no features filters for layer: {}'.format(layer_name))
                return str_error, sqls
            if len(features_by_layer[layer_name]) != len(features_filter_fields_by_layer[layer_name]):
                str_error = ('Different number of features in filters for layer: {}\n'.format(layer_name))
                return str_error, sqls
            for i in range(len(features_by_layer[layer_name])):
                if not isinstance(features_by_layer[layer_name][i], list):
                    str_error = ('In layer: {}, feature: {} is not a list'.format(layer_name, str(i+1)))
                    return str_error, sqls
                feature_filter_fields = features_filter_fields_by_layer[layer_name][i]
                cont_filter_field = 0
                sql = ''
                if db_schema is None:
                    sql = ('UPDATE {} SET '.format(layer_name))
                else:
                    sql = ('UPDATE {}.{} SET '.format(db_schema, layer_name))
                filter_str = ""
                for filter_field_pos in range(len(feature_filter_fields)):
                    filter_field = feature_filter_fields[filter_field_pos]
                    if not isinstance(filter_field, dict):
                        str_error = ('In layer: {}, feature filter: {}, field: {} is not a dictionary'
                                     .format(layer_name, str(i + 1), str(filter_field_pos + 1)))
                        return str_error, sqls
                    if not defs_gdal.FIELD_NAME_TAG in filter_field:
                        str_error = ('In layer: {}, feature: {}, filter field: {} not contains: {}'
                                     .format(layer_name, str(i + 1), str(filter_field_pos), defs_gdal.FIELD_NAME_TAG))
                        return str_error, sqls
                    filter_field_name = filter_field[defs_gdal.FIELD_NAME_TAG]
                    if (filter_field_name == defs_gdal.LAYERS_GEOMETRY_TAG
                            or filter_field_name == defs_gdal.LAYERS_GEOMETRY_POSTGIS_TAG):
                        # to do
                        continue
                    filter_field_type = None
                    if filter_field_name.casefold() != defs_gdal.LAYERS_FIELD_FID_FIELD_NAME.casefold():
                        if not defs_gdal.FIELD_TYPE_TAG in filter_field:
                            str_error = ('In layer: {}, feature: {}, filter field: {} not contains: {}'
                                         .format(layer_name, str(i + 1), str(filter_field_pos + 1), defs_gdal.FIELD_NAME_TAG))
                            return str_error, sqls
                        if not defs_gdal.FIELD_VALUE_TAG in filter_field:
                            str_error = ('In layer: {}, feature: {}, filter field: {} not contains: {}'
                                         .format(layer_name, str(i + 1), str(filter_field_pos + 1), defs_gdal.FIELD_VALUE_TAG))
                            return str_error, sqls
                        filter_field_type = filter_field[defs_gdal.FIELD_TYPE_TAG]
                    else:
                        filter_field_type = defs_gdal.LAYERS_FIELD_FID_FIELD_TYPE
                    filter_field_value = filter_field[defs_gdal.FIELD_VALUE_TAG]
                    if cont_filter_field > 0:
                        filter_str += ' AND '
                    filter_str += filter_field_name
                    filter_str += ' = '
                    if defs_gdal.name_by_type[filter_field_type] == 'string':
                        filter_str += '\''
                    filter_str += str(filter_field_value)
                    if defs_gdal.name_by_type[filter_field_type] == 'string':
                        filter_str += '\''
                    cont_filter_field = cont_filter_field + 1
                feature_fields = features_by_layer[layer_name][i]
                find_geometry_field = False
                cont_value_field = 0
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
                    if not defs_gdal.FIELD_TYPE_TAG in field:
                        str_error = ('In layer: {}, feature: {}, field: {} not contains: {}'
                                     .format(layer_name, str(i + 1), str(field_pos + 1), defs_gdal.FIELD_NAME_TAG))
                        return str_error, sqls
                    field_type = field[defs_gdal.FIELD_TYPE_TAG]
                    if not defs_gdal.FIELD_VALUE_TAG in field:
                        str_error = ('In layer: {}, feature: {}, field: {} not contains: {}'
                                     .format(layer_name, str(i + 1), str(field_pos + 1), defs_gdal.FIELD_VALUE_TAG))
                        return str_error, sqls
                    str_field_value = ''
                    if (field_name == defs_gdal.LAYERS_GEOMETRY_TAG 
                            or field_name == defs_gdal.LAYERS_GEOMETRY_POSTGIS_TAG):
                        wkb_geometry = field[defs_gdal.FIELD_VALUE_TAG]
                        if wkb_geometry != defs_gdal.geometry_type_by_name['none']:
                            geometry = None
                            try:
                                geometry = ogr.CreateGeometryFromWkb(wkb_geometry)
                            except Exception as e:
                                str_error = 'GDAL Error: ' + e.args[0]
                                return str_error, sqls
                            try:
                                str_field_value = geometry.ExportToWkt()
                                # ST_GeomFromText('LINESTRING(27.69858 85.28154, 27.69804 85.28155, 27.69337 85.28174, 27.69356 85.28275, 27.69378 85.28370, 27.69409 85.28449)', 900913)
                                # feature.SetGeometry(geometry)
                                # # feature_geometry = feature.GetGeometryRef()
                                # # feature_wkt = feature_geometry.ExportToWkt()
                                # # yo = 1
                            except Exception as e:
                                str_error = 'GDAL Error: ' + e.args[0]
                                return str_error, sqls
                        else:
                            continue
                    else:
                        field_value = field[defs_gdal.FIELD_VALUE_TAG]
                        if defs_gdal.name_by_type[field_type] == 'string':
                            str_field_value = ('\'{}\''.format(field_value))
                        else:
                            str_field_value = str(field_value)
                    if cont_value_field > 0:
                        sql += ', '
                    sql += field_name
                    sql += ' = '
                    sql += str_field_value
                    cont_value_field = cont_value_field + 1
                sql += ' WHERE ' + filter_str
                sqls.append(sql)
        return str_error, sqls

    @classmethod
    def get_sql_write_features(self,
                               features_by_layer,
                               db_schema = None):
        str_error = ''
        sqls = []
        if not db_schema is None:
            if not isinstance(db_schema, str):
                str_error = ('db_schema must be a string')
                return str_error, sqls
        if not isinstance(features_by_layer, dict):
            str_error = ('Features by layer argument must be a dictionary of lists')
            return str_error, sqls
        for layer_name in features_by_layer:
            if not isinstance(features_by_layer[layer_name], list):
                str_error = ('Features by layer argument must be a dictionary of lists')
                return str_error, sqls
        for layer_name in features_by_layer:
            for i in range(len(features_by_layer[layer_name])):
                if not isinstance(features_by_layer[layer_name][i], list):
                    str_error = ('In layer: {}, feature: {} is not a list'.format(layer_name, str(i + 1)))
                    return str_error, sqls
                feature_fields = features_by_layer[layer_name][i]
                find_geometry_field = False
                # feature = ogr.Feature(layer.GetLayerDefn())  # instantiate OGRFeature
                sql = 'INSERT INTO '
                if not db_schema is None:
                    sql += (db_schema + '.')
                sql += (layer_name + '(')
                inserted_fields = 0
                for field_pos in range(len(feature_fields)):
                    field = feature_fields[field_pos]
                    if not isinstance(field, dict):
                        str_error = ('In layer: {}, feature: {}, field: {} is not a dictionary'
                                     .format(layer_name, str(i + 1), str(field_pos)))
                        return str_error, sqls
                    if not defs_gdal.FIELD_NAME_TAG in field:
                        str_error = ('In layer: {}, feature: {}, field: {} not contains: {}'
                                     .format(layer_name, str(i + 1), str(field_pos), defs_gdal.FIELD_NAME_TAG))
                        return str_error, sqls
                    field_name = field[defs_gdal.FIELD_NAME_TAG]
                    if field_name == defs_gdal.LAYERS_GEOMETRY_POSTGIS_TAG:
                        find_geometry_field = True
                        wkb_geometry = field[defs_gdal.FIELD_VALUE_TAG]
                        if wkb_geometry == defs_gdal.geometry_type_by_name['none']:
                            continue
                    if inserted_fields > 0:
                        sql += ','
                    sql += field_name
                    inserted_fields = inserted_fields + 1
                sql += ') VALUES('
                if not find_geometry_field:
                    str_error = ('In layer: {}, feature: {}, not contains geometry field'
                                 .format(layer_name, str(i + 1)))
                    return str_error, sqls
                inserted_fields = 0
                for field_pos in range(len(feature_fields)):
                    field = feature_fields[field_pos]
                    field_name = field[defs_gdal.FIELD_NAME_TAG]
                    str_field_value = ''
                    if field_name == defs_gdal.LAYERS_GEOMETRY_POSTGIS_TAG:
                        wkb_geometry = field[defs_gdal.FIELD_VALUE_TAG]
                        if wkb_geometry != defs_gdal.geometry_type_by_name['none']:
                            geometry = None
                            try:
                                geometry = ogr.CreateGeometryFromWkb(wkb_geometry)
                            except Exception as e:
                                str_error = 'GDAL Error: ' + e.args[0]
                                return str_error, sqls
                            try:
                                str_field_value = geometry.ExportToWkt()
                                # ST_GeomFromText('LINESTRING(27.69858 85.28154, 27.69804 85.28155, 27.69337 85.28174, 27.69356 85.28275, 27.69378 85.28370, 27.69409 85.28449)', 900913)
                                # feature.SetGeometry(geometry)
                                # # feature_geometry = feature.GetGeometryRef()
                                # # feature_wkt = feature_geometry.ExportToWkt()
                                # # yo = 1
                            except Exception as e:
                                str_error = 'GDAL Error: ' + e.args[0]
                                return str_error, sqls
                        else:
                            continue
                    else:
                        if not defs_gdal.FIELD_TYPE_TAG in field:
                            str_error = ('In layer: {}, feature: {}, field: {} not contains: {}'
                                         .format(layer_name, str(i + 1), str(field_pos), defs_gdal.FIELD_NAME_TAG))
                            return str_error, sqls
                        if not defs_gdal.FIELD_VALUE_TAG in field:
                            str_error = ('In layer: {}, feature: {}, field: {} not contains: {}'
                                         .format(layer_name, str(i + 1), str(field_pos), defs_gdal.FIELD_VALUE_TAG))
                            return str_error, sqls
                        field_type = field[defs_gdal.FIELD_TYPE_TAG]
                        field_value = field[defs_gdal.FIELD_VALUE_TAG]
                        if defs_gdal.name_by_type[field_type] == 'string':
                            str_field_value = ('\'{}\''.format(field_value))
                        else:
                            str_field_value = str(field_value)
                    # add to sql
                    if inserted_fields > 0:
                        sql += ','
                    sql += str_field_value
                    inserted_fields = inserted_fields + 1
                sql += ')'
                sqls.append(sql)
        return str_error, sqls
