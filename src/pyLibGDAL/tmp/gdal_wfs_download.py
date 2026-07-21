from osgeo import gdal, ogr
gdal.UseExceptions()
# gdal.SetConfigOption('CPL_DEBUG', 'ON')
#
gdal.SetConfigOption('OGR_WFS_PAGING_ALLOWED', 'ON')
gdal.SetConfigOption('OGR_WFS_PAGE_SIZE', '250')
gdal.SetConfigOption('GDAL_HTTP_AUTH', 'BASIC')#=[BASIC/NTLM/GSSNEGOTIATE/ANY]
gdal.SetConfigOption('GDAL_HTTP_USERPWD', 'user_project_126:uxw0b9HMaQ487YC9')
yo = 1
# gdal.SetConfigOption('GDAL_HTTP_USERPWD', '')
# ds = gdal.OpenEx('WFS:http://163.172.31.229:8081/geoserver/ows?service=WFS', gdal.OF_VECTOR)
# ds = gdal.OpenEx('WFS:http://163.172.31.229:8081/geoserver/ows?service=WFS&acceptversions=2.0.0&request=GetCapabilities', gdal.OF_VECTOR)
ds = ogr.Open('WFS:http://163.172.31.229:8081/geoserver/ows?service=WFS&acceptversions=2.0.0&request=GetCapabilities')
#
# layer_names = [l.GetName() for l in ogr.Open(file_path)]
# print(ds)
# '''
for i in range(ds.GetLayerCount()):
    layer = ds.GetLayerByIndex(i)
    srs = layer.GetSpatialRef()
    layer_defn = layer.GetLayerDefn()
    layer_geom_type = layer_defn.GetGeomType()
    layer_geom_name = ogr.GeometryTypeToName(layer_geom_type)
    print('Layer: %s, Features: %s, SR: %s...' % (layer.GetName(), layer.GetFeatureCount(), srs.ExportToWkt()[0:50]))
# '''
yo = 2
# with gdal.config_options({
#     'OGR_WFS_PAGING_ALLOWED': 'ON',
#     'OGR_WFS_PAGE_SIZE': '250'
#     # 'GDAL_HTTP_AUTH' : 'BASIC',#=[BASIC/NTLM/GSSNEGOTIATE/ANY]
#     # 'GDAL_HTTP_USERPWD' : 'user_project_126:uxw0b9HMaQ487YC9'
# }):
    # ds = gdal.OpenEx('WFS:https://data.geopf.fr/wfs/wfs', gdal.OF_VECTOR)
    # # Full dataset
    # gdal.VectorTranslate(
    #     'demo.gpkg',
    #     ds,
    #     options='-f GPKG -nln communes ADMINEXPRESS-COG-CARTO.LATEST:commune'
    # )
    # # Filtered using bbox with -spat option (escaped negative coordinates)
    # gdal.VectorTranslate(
    #     'demo.gpkg',
    #     ds,
    #     options='-f GPKG -update -nln com_bbox1 -spat \-0.1 46.6 0.2 46.9 ADMINEXPRESS-COG-CARTO.LATEST:commune'
    # )
    # # Filtered using bbox with -spat option (escaped negative coordinates)
    # # Output CSV to stdout
    # gdal.VectorTranslate(
    #     '/vsistdout/',
    #     ds,
    #     options='-f CSV -nln com_bbox1 -spat \-0.1 46.6 0.2 46.9 ADMINEXPRESS-COG-CARTO.LATEST:commune'
    # )
    # # Filtered using bbox with -spat option (escaped negative coordinates)
    # # Output CSV to file
    # gdal.VectorTranslate(
    #     'demo.csv',
    #     ds,
    #     options='-f CSV -nln com_bbox1 -spat \-0.1 46.6 0.2 46.9 ADMINEXPRESS-COG-CARTO.LATEST:commune'
    # )
    # # Make http calls that return GeoJSON instead of WFS (lighter but not supported by all WFS services)
    # ds = gdal.OpenEx('WFS:https://data.geopf.fr/wfs/wfs?outputFormat=json', gdal.OF_VECTOR)
    # # Filtered using bbox with -spat option (escaped negative coordinates)
    # # Output GeoJSON to file
    # gdal.VectorTranslate(
    #     'demo.geojson',
    #     ds,
    #     options='-f GeoJSON -nln com_bbox1 -spat \-0.1 46.6 0.2 46.9 ADMINEXPRESS-COG-CARTO.LATEST:commune'
    # )