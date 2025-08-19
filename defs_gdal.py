# authors:
# David Hernandez Lopez, david.hernandez@uclm.es

from osgeo import ogr, gdal

MAX_PERCENTAGE_AVAILABLE_RAM_TO_USE = 80.
GDAL_TAG_RASTER = 'DCAP_RASTER'
GDAL_TAG_VECTOR = 'DCAP_VECTOR'

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
geometry_type_by_name['point'] = ogr.wkbPoint
geometry_name_by_type[ogr.wkbPoint] = 'point'
geometry_type_by_name['linestring'] = ogr.wkbLineString
geometry_name_by_type[ogr.wkbLineString] = 'linestring'
geometry_type_by_name['geometry_collection'] = ogr.wkbGeometryCollection
geometry_name_by_type[ogr.wkbGeometryCollection] = 'geometry_collection'
geometry_type_by_name['multipolygon'] = ogr.wkbMultiPolygon
geometry_name_by_type[ogr.wkbMultiPolygon] = 'multipolygon'
geometry_type_by_name['multipoint'] = ogr.wkbMultiPoint
geometry_name_by_type[ogr.wkbMultiPoint] = 'multipoint'
geometry_type_by_name['multilinestring'] = ogr.wkbMultiLineString
geometry_name_by_type[ogr.wkbMultiLineString] = 'multilinestring'
geometry_type_by_name['polygon_m'] = ogr.wkbPolygonM
geometry_name_by_type[ogr.wkbPolygonM] = 'polygon_m'
geometry_type_by_name['point_m'] = ogr.wkbPointM
geometry_name_by_type[ogr.wkbPointM] = 'point_m'
geometry_type_by_name['linestring_m'] = ogr.wkbLineStringM
geometry_name_by_type[ogr.wkbLineStringM] = 'linestring_m'
geometry_type_by_name['geometry_collection_m'] = ogr.wkbGeometryCollectionM
geometry_name_by_type[ogr.wkbGeometryCollectionM] = 'geometry_collection_m'
geometry_type_by_name['multipolygon_m'] = ogr.wkbMultiPolygonM
geometry_name_by_type[ogr.wkbMultiPolygonM] = 'multipolygon_m'
geometry_type_by_name['multipoint_m'] = ogr.wkbMultiPointM
geometry_name_by_type[ogr.wkbMultiPointM] = 'multipoint_m'
geometry_type_by_name['multilinestring_m'] = ogr.wkbMultiLineStringM
geometry_name_by_type[ogr.wkbMultiLineStringM] = 'multilinestring_m'
geometry_type_by_name['polygon_zm'] = ogr.wkbPolygonZM
geometry_name_by_type[ogr.wkbPolygonZM] = 'polygon_zm'
geometry_type_by_name['point_zm'] = ogr.wkbPointZM
geometry_name_by_type[ogr.wkbPointZM] = 'point_zm'
geometry_type_by_name['linestring_zm'] = ogr.wkbLineStringZM
geometry_name_by_type[ogr.wkbLineStringZM] = 'linestring_zm'
geometry_type_by_name['geometry_collection_zm'] = ogr.wkbGeometryCollectionZM
geometry_name_by_type[ogr.wkbGeometryCollectionZM] = 'geometry_collection_zm'
geometry_type_by_name['multipolygon_zm'] = ogr.wkbMultiPolygonZM
geometry_name_by_type[ogr.wkbMultiPolygonZM] = 'multipolygon_zm'
geometry_type_by_name['multipoint_zm'] = ogr.wkbMultiPointZM
geometry_name_by_type[ogr.wkbMultiPointZM] = 'multipoint_zm'
geometry_type_by_name['multilinestring_zm'] = ogr.wkbMultiLineStringZM
geometry_name_by_type[ogr.wkbMultiLineStringZM] = 'multilinestring_zm'
geometry_type_by_name['polygon_25d'] = ogr.wkbPolygon25D
geometry_name_by_type[ogr.wkbPolygon25D] = 'polygon_25d'
geometry_type_by_name['point_25d'] = ogr.wkbPoint25D
geometry_name_by_type[ogr.wkbPoint25D] = 'point_25d'
geometry_type_by_name['linestring_25d'] = ogr.wkbLineString25D
geometry_name_by_type[ogr.wkbLineString25D] = 'linestring_25d'
geometry_type_by_name['geometry_collection_25d'] = ogr.wkbGeometryCollection25D
geometry_name_by_type[ogr.wkbGeometryCollection25D] = 'geometry_collection_25d'
geometry_type_by_name['multipolygon_25d'] = ogr.wkbMultiPolygon25D
geometry_name_by_type[ogr.wkbMultiPolygon25D] = 'multipolygon_25d'
geometry_type_by_name['multipoint_25d'] = ogr.wkbMultiPoint25D
geometry_name_by_type[ogr.wkbMultiPoint25D] = 'multipoint_25d'
geometry_type_by_name['multilinestring_25d'] = ogr.wkbMultiLineString25D
geometry_name_by_type[ogr.wkbMultiLineString25D] = 'multilinestring_25d'

RASTER_FULL_PRECISION_CODE = -1
gdal_bytes_by_type = {}
gdal_bytes_by_type[1] = 1
gdal_bytes_by_type[2] = 2
gdal_bytes_by_type[3] = 2
gdal_bytes_by_type[4] = 4
gdal_bytes_by_type[5] = 4
gdal_bytes_by_type[6] = 4
gdal_bytes_by_type[7] = 8
# gdal_bytes_by_type[8] = 1
# gdal_bytes_by_type[9] = 1
# gdal_bytes_by_type[10] = 1
# gdal_bytes_by_type[11] = 1
# GDAL Raster Data Types
# Unknown or unspecified type gdalconst.GDT_Unknown 0
# 8-bit inconsistent integers gdalconst.GDT_Byte 1
# 16-bit inconsistent integers gdalconst.GDT_UInt16 2
# 16 bit integer gdalconst.GDT_Int16 3
# 32-bit inconsistent integers gdalconst.GDT_UInt32 4
# 32-bit integer value gdalconst.GDT_Int32 5
# 32-bit floating-point type gdalconst.GDT_Float32 6
# 64-bit floating-point type gdalconst.GDT_Float64 7
# 16-bit Complex integer gdalconst.GDT_CInt16 8
# 32-bit Complex integer gdalconst.GDT_CInt32 9
# 32-bit complex floating-point type gdalconst.GDT_CFloat32 10
# 64-bit complex floating-point type gdalconst.GDT_CFloat64 11
