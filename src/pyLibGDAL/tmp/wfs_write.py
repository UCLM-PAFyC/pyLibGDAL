from osgeo import gdal, ogr

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
# ds = gdal.OpenEx('WFS:http://163.172.31.229:8081/geoserver/ows?service=WFS&VERSION==2.0.0', gdal.OF_VECTOR, 1)
driver = ogr.GetDriverByName('WFS')
VERSION = '1.1.0'
ds = driver.Open("WFS:http://163.172.31.229:8081/geoserver/ows?service=WFS&VERSION={}".format(VERSION), True)
assert ds is not None, gdal.GetLastErrorMsg()
layer = ds.GetLayerByName('locations')
assert layer is not None, gdal.GetLastErrorMsg()
wfslayer_defn = layer.GetLayerDefn()
new_feature = ogr.Feature(layer.GetLayerDefn())
new_feature.SetField( 'temp', "roi_python_5" )
new_feature.SetField( 'content', "roi_python_5" )
geom = ogr.CreateGeometryFromWkt('POLYGON ((622592.803049483 4327496.20480056,627640.688173881 4327496.20480056,627640.688173881 4330097.23989786,622592.803049483 4330097.23989786,622592.803049483 4327496.20480056))')
new_feature.SetGeometry(geom)
str_error = None
try:
    err = layer.CreateFeature(new_feature)
except Exception as e:
    str_error = 'GDAL Error: ' + e.args[0]
# assert err == 0, gdal.GetLastErrorMsg()
# Cleanup
fid = new_feature.GetFID()
new_feature = None
wfs_ds = None
yo = 1

# err = layer.DeleteFeature(fid)
# assert err == 0, gdal.GetLastErrorMsg()
# yo = 1
#
#
# VERSION = '2.0.0'
#
# # With 1.0.0 everything works fine, uncomment this line to check
# # VERSION = '1.0.0'
#
# driver = ogr.GetDriverByName('WFS')
# wfs_ds = driver.Open("WFS:https://demo.nextgis.com/api/resource/5029/wfs?VERSION={}".format(VERSION), True)
#
# assert wfs_ds is not None, gdal.GetLastErrorMsg()
#
# wfslayer_type = wfs_ds.GetLayerByName('point')
# assert wfslayer_type is not None, gdal.GetLastErrorMsg()
#
# feature = ogr.Feature(wfslayer_type.GetLayerDefn())
#
# geom = ogr.CreateGeometryFromWkt('POINT (0 0)')
# feature.SetGeometry(geom)
#
# err = wfslayer_type.CreateFeature(feature)
# assert err == 0, gdal.GetLastErrorMsg()
#
# fid = feature.GetFID()
# err = wfslayer_type.DeleteFeature(fid)
# assert err == 0, gdal.GetLastErrorMsg()