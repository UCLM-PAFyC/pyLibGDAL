# authors:
# David Hernandez Lopez, david.hernandez@uclm.es

from osgeo import ogr

LAYERS_FIELDS_TAG = 'fields'
LAYERS_GEOMETRY_TAG = 'geometry'
LAYERS_GEOMETRY_TYPE_TAG = 'geometry_type'
FIELD_NAME_TAG = 'field_name'
FIELD_TYPE_TAG = 'field_type'
FIELD_VALUE_TAG = 'field_value'

type_by_name = {}
name_by_type = {}
type_by_name['string'] = ogr.OFTString
name_by_type[ogr.OFTString] = 'string'
type_by_name['int'] = ogr.OFTInteger
name_by_type[ogr.OFTInteger] = 'int'
type_by_name['real'] = ogr.OFTReal
name_by_type[ogr.OFTReal] = 'real'

geometry_type_by_name = {}
geometry_name_by_type = {}
geometry_type_by_name['none'] = ogr.wkbNone
geometry_name_by_type[ogr.wkbNone] = 'none'
geometry_type_by_name['polygon'] = ogr.wkbPolygon
geometry_name_by_type[ogr.wkbPolygon] = 'polygon'
# geometry_type_by_name['int'] = ogr.OFTInteger
# geometry_name_by_type[ogr.OFTInteger] = 'int'
# geometry_type_by_name['real'] = ogr.OFTReal
# geometry_name_by_type[ogr.OFTReal] = 'real'

