# authors:
# David Hernandez Lopez, david.hernandez@uclm.es

from osgeo import ogr, gdal

WFS_WRITE_VERSION = 'VERSION=1.1.0'

MAX_PERCENTAGE_AVAILABLE_RAM_TO_USE = 80.
INTERPOLATION_METHOD_BILINEAR = 'bilinear'
INTERPOLATION_METHOD_BICUBIC = 'bicubic'

RASTER_DEM_FULL_PRECISION_CODE = -1
RASTER_DEM_CENTIMETER_PRECISION_CODE = 2
RASTER_DEM_MILLIMETER_PRECISION_CODE = 3

GDAL_TAG_RASTER = 'DCAP_RASTER'
GDAL_TAG_VECTOR = 'DCAP_VECTOR'
GDAL_ALIAS_RASTER = 'raster'
GDAL_ALIAS_VECTOR = 'vector'

LAYERS_FIELD_FID_FIELD_NAME = 'fid'
LAYERS_FIELD_FID_FIELD_TYPE = ogr.OFTInteger
LAYERS_FIELDS_TAG = 'fields'
LAYERS_GEOMETRY_TAG = 'geometry'
LAYERS_GEOMETRY_POSTGIS_TAG = 'geom'
LAYERS_GEOMETRY_TYPE_TAG = 'geometry_type'
FIELD_NAME_TAG = 'field_name'
FIELD_TYPE_TAG = 'field_type'
FIELD_VALUE_TAG = 'field_value'
FIELD_FID_NAME = 'fid'
POSTGIS_FIELD_FID_NAME = 'id'

GEOPACKAGE_FILE_EXTENSION = '.gpkg'
GEOPACKAGE_GET_LAYERS_SQL = 'SELECT * FROM gpkg_contents;'
GEOPACKAGE_GET_LAYERS_LAYER_NAME_POSITION = 0
GEOPACKAGE_GET_LAYERS_LAYER_TYPE_POSITION = 1
GEOPACKAGE_GET_LAYERS_LAYER_TYPE_VECTOR = 'features'
GEOPACKAGE_GET_LAYERS_LAYER_TYPE_ATTRIBUTES = 'attributes'
GEOPACKAGE_GET_LAYERS_LAYER_TYPE_RASTER = ['tiles', '2d-gridded-coverage']
GEOPACKAGE_TABLE_LAYER_STYLES = 'layer_styles'
GEOPACKAGE_TABLE_LAYER_STYLES_FIELD_LAYER_NAME = 'f_table_name'
GEOPACKAGE_TABLE_LAYER_STYLES_FIELD_LAYER_STYLE_NAME = 'styleName'
GEOPACKAGE_TABLE_LAYER_STYLES_FIELD_USE_AS_DEFAULT = 'useAsDefault'

type_by_name = {}
name_by_type = {}
type_by_name['string'] = ogr.OFTString
name_by_type[ogr.OFTString] = 'string'
type_by_name['int'] = ogr.OFTInteger
name_by_type[ogr.OFTInteger] = 'int'
type_by_name['real'] = ogr.OFTReal
name_by_type[ogr.OFTReal] = 'real'
postgis_type_by_ogr_type = {}
postgis_type_by_ogr_type[ogr.OFTString] = 'text'
postgis_type_by_ogr_type[ogr.OFTInteger] = 'integer'
postgis_type_by_ogr_type[ogr.OFTReal] = 'real'

postgis_geometry_type_by_ogr_type = {}
geometry_type_by_name = {}
geometry_name_by_type = {}
geometry_type_by_name['none'] = ogr.wkbNone
geometry_name_by_type[ogr.wkbNone] = 'none'
postgis_geometry_type_by_ogr_type[ogr.wkbNone] = 'none'
geometry_type_by_name['polygon'] = ogr.wkbPolygon
geometry_name_by_type[ogr.wkbPolygon] = 'polygon'
postgis_geometry_type_by_ogr_type[ogr.wkbPolygon] = 'POLYGON'
geometry_type_by_name['point'] = ogr.wkbPoint
geometry_name_by_type[ogr.wkbPoint] = 'point'
postgis_geometry_type_by_ogr_type[ogr.wkbPoint] = 'POINT'
geometry_type_by_name['linestring'] = ogr.wkbLineString
geometry_name_by_type[ogr.wkbLineString] = 'linestring'
postgis_geometry_type_by_ogr_type[ogr.wkbLineString] = 'LINESTRING'
geometry_type_by_name['geometry_collection'] = ogr.wkbGeometryCollection
geometry_name_by_type[ogr.wkbGeometryCollection] = 'geometry_collection'
postgis_geometry_type_by_ogr_type[ogr.wkbGeometryCollection] = 'GEOMETRYCOLLECTION'
geometry_type_by_name['multipolygon'] = ogr.wkbMultiPolygon
geometry_name_by_type[ogr.wkbMultiPolygon] = 'multipolygon'
postgis_geometry_type_by_ogr_type[ogr.wkbMultiPolygon] = 'MULTIPOLYGON'
geometry_type_by_name['multipoint'] = ogr.wkbMultiPoint
geometry_name_by_type[ogr.wkbMultiPoint] = 'multipoint'
postgis_geometry_type_by_ogr_type[ogr.wkbMultiPoint] = 'MULTIPOINT'
geometry_type_by_name['multilinestring'] = ogr.wkbMultiLineString
geometry_name_by_type[ogr.wkbMultiLineString] = 'multilinestring'
postgis_geometry_type_by_ogr_type[ogr.wkbMultiLineString] = 'MULTILINESTRING'
geometry_type_by_name['polygon_m'] = ogr.wkbPolygonM
geometry_name_by_type[ogr.wkbPolygonM] = 'polygon_m'
postgis_geometry_type_by_ogr_type[ogr.wkbPolygonM] = 'POLYGON'
geometry_type_by_name['point_m'] = ogr.wkbPointM
geometry_name_by_type[ogr.wkbPointM] = 'point_m'
postgis_geometry_type_by_ogr_type[ogr.wkbPointM] = 'POINT'
geometry_type_by_name['linestring_m'] = ogr.wkbLineStringM
geometry_name_by_type[ogr.wkbLineStringM] = 'linestring_m'
postgis_geometry_type_by_ogr_type[ogr.wkbLineStringM] = 'LINESTRING'
geometry_type_by_name['geometry_collection_m'] = ogr.wkbGeometryCollectionM
geometry_name_by_type[ogr.wkbGeometryCollectionM] = 'geometry_collection_m'
postgis_geometry_type_by_ogr_type[ogr.wkbGeometryCollectionM] = 'GEOMETRYCOLLECTION'
geometry_type_by_name['multipolygon_m'] = ogr.wkbMultiPolygonM
geometry_name_by_type[ogr.wkbMultiPolygonM] = 'multipolygon_m'
postgis_geometry_type_by_ogr_type[ogr.wkbMultiPolygonM] = 'MULTIPOLYGON'
geometry_type_by_name['multipoint_m'] = ogr.wkbMultiPointM
geometry_name_by_type[ogr.wkbMultiPointM] = 'multipoint_m'
postgis_geometry_type_by_ogr_type[ogr.wkbMultiPointM] = 'MULTIPOINT'
geometry_type_by_name['multilinestring_m'] = ogr.wkbMultiLineStringM
geometry_name_by_type[ogr.wkbMultiLineStringM] = 'multilinestring_m'
postgis_geometry_type_by_ogr_type[ogr.wkbMultiLineStringM] = 'MULTILINESTRING'
geometry_type_by_name['polygon_zm'] = ogr.wkbPolygonZM
geometry_name_by_type[ogr.wkbPolygonZM] = 'polygon_zm'
postgis_geometry_type_by_ogr_type[ogr.wkbPolygonZM] = 'POLYGON'
geometry_type_by_name['point_zm'] = ogr.wkbPointZM
geometry_name_by_type[ogr.wkbPointZM] = 'point_zm'
postgis_geometry_type_by_ogr_type[ogr.wkbPointZM] = 'POINT'
geometry_type_by_name['linestring_zm'] = ogr.wkbLineStringZM
geometry_name_by_type[ogr.wkbLineStringZM] = 'linestring_zm'
postgis_geometry_type_by_ogr_type[ogr.wkbLineStringZM] = 'LINESTRING'
geometry_type_by_name['geometry_collection_zm'] = ogr.wkbGeometryCollectionZM
geometry_name_by_type[ogr.wkbGeometryCollectionZM] = 'geometry_collection_zm'
postgis_geometry_type_by_ogr_type[ogr.wkbGeometryCollectionZM] = 'GEOMETRYCOLLECTION'
geometry_type_by_name['multipolygon_zm'] = ogr.wkbMultiPolygonZM
geometry_name_by_type[ogr.wkbMultiPolygonZM] = 'multipolygon_zm'
postgis_geometry_type_by_ogr_type[ogr.wkbMultiPolygonZM] = 'MULTIPOLYGON'
geometry_type_by_name['multipoint_zm'] = ogr.wkbMultiPointZM
geometry_name_by_type[ogr.wkbMultiPointZM] = 'multipoint_zm'
postgis_geometry_type_by_ogr_type[ogr.wkbMultiPointZM] = 'MULTIPOINT'
geometry_type_by_name['multilinestring_zm'] = ogr.wkbMultiLineStringZM
geometry_name_by_type[ogr.wkbMultiLineStringZM] = 'multilinestring_zm'
postgis_geometry_type_by_ogr_type[ogr.wkbMultiLineStringZM] = 'MULTILINESTRING'
geometry_type_by_name['polygon_25d'] = ogr.wkbPolygon25D
geometry_name_by_type[ogr.wkbPolygon25D] = 'polygon_25d'
postgis_geometry_type_by_ogr_type[ogr.wkbPolygon25D] = 'POLYGON'
geometry_type_by_name['point_25d'] = ogr.wkbPoint25D
geometry_name_by_type[ogr.wkbPoint25D] = 'point_25d'
postgis_geometry_type_by_ogr_type[ogr.wkbPoint25D] = 'POINT'
geometry_type_by_name['linestring_25d'] = ogr.wkbLineString25D
geometry_name_by_type[ogr.wkbLineString25D] = 'linestring_25d'
postgis_geometry_type_by_ogr_type[ogr.wkbLineString25D] = 'LINESTRING'
geometry_type_by_name['geometry_collection_25d'] = ogr.wkbGeometryCollection25D
geometry_name_by_type[ogr.wkbGeometryCollection25D] = 'geometry_collection_25d'
postgis_geometry_type_by_ogr_type[ogr.wkbGeometryCollection25D] = 'GEOMETRYCOLLECTION'
geometry_type_by_name['multipolygon_25d'] = ogr.wkbMultiPolygon25D
geometry_name_by_type[ogr.wkbMultiPolygon25D] = 'multipolygon_25d'
postgis_geometry_type_by_ogr_type[ogr.wkbMultiPolygon25D] = 'MULTIPOLYGON'
geometry_type_by_name['multipoint_25d'] = ogr.wkbMultiPoint25D
geometry_name_by_type[ogr.wkbMultiPoint25D] = 'multipoint_25d'
postgis_geometry_type_by_ogr_type[ogr.wkbMultiPoint25D] = 'MULTIPOINT'
geometry_type_by_name['multilinestring_25d'] = ogr.wkbMultiLineString25D
geometry_name_by_type[ogr.wkbMultiLineString25D] = 'multilinestring_25d'
postgis_geometry_type_by_ogr_type[ogr.wkbMultiLineString25D] = 'MULTILINESTRING'

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
