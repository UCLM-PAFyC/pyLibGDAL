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
            if not defs_gdal.LAYERS_GEOMETRY_TAG in layers[layer_name]:
                str_error = ('All layers must has a geometry field, type none for no geometry')
                return str_error, sqls
            # if not layers[layer_name][defs_gdal.LAYERS_GEOMETRY_TAG] in defs_gdal.geometry_type_by_name:
            if not layers[layer_name][defs_gdal.LAYERS_GEOMETRY_TAG] in defs_gdal.geometry_name_by_type:
                str_error = ('All layers must has a valid geometry field, type none for no geometry')
                return str_error, sqls
            if not layer_name in layers_crs_id:
                str_error = ('All layers must has a CRS Id, in layers CRS id argument')
                return str_error, sqls
        postgis_geometry_type = None
        for layer_name in layers:
            geometry_type = layers[layer_name][defs_gdal.LAYERS_GEOMETRY_TAG]
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
            sql += 'gid INTEGER NOT NULL PRIMARY KEY'
            for field_name in layers[layer_name]:
                if field_name == defs_gdal.LAYERS_GEOMETRY_TAG:
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
                    sql = ('SELECT AddGeometryColumn(\'{}\',\'{}\',{},\'{}\',3)'
                           .format(layer_name, defs_gdal.LAYERS_GEOMETRY_TAG,
                                   srs_id, postgis_geometry_type))
                else:
                    sql = ('SELECT AddGeometryColumn(\'{}\',\'{}\',\'{}\',{},\'{}\',3)'
                           .format(db_schema,layer_name, defs_gdal.LAYERS_GEOMETRY_TAG,
                                   srs_id, postgis_geometry_type))
                sqls.append(sql)
        return str_error, sqls
