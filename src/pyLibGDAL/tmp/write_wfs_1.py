from osgeo import gdal, ogr, osr

gdal.SetConfigOption('OGR_WFS_PAGING_ALLOWED', 'ON')
gdal.SetConfigOption('OGR_WFS_PAGE_SIZE', '250')
gdal.SetConfigOption('GDAL_HTTP_AUTH', 'BASIC')#=[BASIC/NTLM/GSSNEGOTIATE/ANY]
gdal.SetConfigOption('GDAL_HTTP_USERPWD', 'user_project_126:uxw0b9HMaQ487YC9')

# 1. Open WFS connection in update mode
# driver = ogr.GetDriverByName('WFS')
wfs_url = "WFS:http://163.172.31.229:8081/geoserver/ows?service=WFS&VERSION=1.0.0" # Or 2.0.0
# wfs_ds = driver.Open(wfs_url, True) # True for WFS-T (transactional)

url = 'http://163.172.31.229:8081/geoserver/ows?service=WFS&acceptversions=2.0.0&request=GetCapabilities'
url_parts = url.split('?')
wfs_write_version = 'VERSION=1.1.0'
wfs_url = ("WFS:{}?service=WFS&{}".format(url_parts[0], wfs_write_version)) # Or 2.0.0

wfs_ds = ogr.Open(wfs_url, update = 1)
if wfs_ds is None:
    print("Could not open WFS")
    exit()

# 2. Get the target layer
layer_name = 'locations'
layer = wfs_ds.GetLayerByName(layer_name)
if layer is None:
    print(f"Layer '{layer_name}' not found")
    exit()

# 3. Define a new feature
feature_defn = layer.GetLayerDefn()
new_feature = ogr.Feature(feature_defn)
new_feature.SetField('temp', 'roi_pygdal_1') # Set attributes
# poFeature->SetFID(1000);
geom = ogr.CreateGeometryFromWkt('POLYGON ((622592.803049483 4327496.20480056,627640.688173881 4327496.20480056,627640.688173881 4330097.23989786,622592.803049483 4330097.23989786,622592.803049483 4327496.20480056))') # Set geometry
new_feature.SetGeometry(geom)

# 4. Insert the feature
if layer.CreateFeature(new_feature) == ogr.OGRERR_NONE:
    print("Feature inserted successfully!")
else:
    print("Failed to insert feature.")

# Cleanup
new_feature = None
wfs_ds = None