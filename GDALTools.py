# authors:
# David Hernandez Lopez, david.hernandez@uclm.es

import os, sys
from osgeo import gdal, osr, ogr

import subprocess

current_path = os.path.dirname(__file__)
sys.path.append(os.path.join(current_path, '..'))

from . import defs_gdal
from pyLibCRSs import CRSsDefines as defs_crs
from pyLibCRSs.CRSsTools import CRSsTools

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
gdal.UseExceptions()  # Exceptions will get raised on anything >= gdal.CE_Failure
assert err.err_level == gdal.CE_None, 'the error level starts at 0'

class GDALTools(object):
    is_initialized = False
    crs_tools = None
    driver_names_by_file_extension = {}
    vector_drivers_file_extensions = []
    raster_drivers_file_extensions = []

    @classmethod
    def create_vector(self,
                      file_path,
                      layers,
                      layers_crs_id,
                      ignore_existing_layers,
                      create_options = None):
        str_error = ''
        if not isinstance(file_path, str):
            str_error = ('File path must be a string and is a: {}'.format(str(type(file_path))))
            return str_error
        if not self.is_initialized:
            str_error = self.initialize()
            if str_error:
                return str_error
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
        str_error, is_vector = self.is_vector(file_path)
        if str_error:
            return str_error
        if not is_vector:
            str_error = ('File is not a vector data source:\n{}'.format(file_path))
            return str_error
        str_error, driver_names = self.get_driver_name_from_file(file_path)
        if str_error:
            return str_error
        # driver = ogr.GetDriverByName("GPKG")
        ds = None
        for i in range(len(driver_names)):
            driver_name = driver_names[i]
            driver = ogr.GetDriverByName(driver_name)
            try:
                if not ignore_existing_layers:
                    if create_options:
                        ds = driver.CreateDataSource(file_path, create_options)
                    else:
                        ds = driver.CreateDataSource(file_path)
                else:
                    ds = driver.Open(file_path, update=1)
                break
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
                    # to do, remove_features?
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

    @classmethod
    def exists_layer(self, file_path, layer_name):
        str_error = ''
        exists_layer = False
        str_error, layer_names = self.get_layers_names(file_path)
        if not str_error:
            if layer_name in layer_names:
                exists_layer = True
        return str_error, exists_layer

    @classmethod
    def gdalinfo_as_json(self, file_path): # https://gdal.org/en/stable/programs/gdal_cli_from_python.html, 3.11
        str_error = ''
        info_as_json = ''
        if not isinstance(file_path, str):
            str_error = ('File path must be a string and is a: {}'.format(str(type(file_path))))
            return str_error
        if not self.is_initialized:
            str_error = self.initialize()
            if str_error:
                return str_error, info_as_json
        str_error = ''
        if not isinstance(file_path, str):
            str_error = ('File path must be a string and is a: {}'.format(str(type(file_path))))
            return str_error, info_as_json
        if not self.is_initialized:
            str_error = self.initialize()
            if str_error:
                return str_error, info_as_json
        command = ("gdalinfo -json \"{}\"".format(file_path))
        try:
            res = subprocess.Popen(command,
                                   universal_newlines=True,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
            info_as_json, error = res.communicate()
            if error:
                str_error = ('In command:\{}\nError:\n{}'.format(command, error.strip()))
                return str_error, info_as_json
        # except CalledProcessError as e:
        #   print "CalledError > ",e.returncode
        #   print "CalledError > ",e.output
        except OSError as e:
            str_error = ('In command:\{}\nError:\n{}\n{}\n{}'.format(command, e.errno, e.strerror, e.filename))
            return str_error, info_as_json
        except:
            str_error = ('In command:\{}\nError:\n{}'.format(command, sys.exc_info()[0]))
            return str_error, info_as_json
        return str_error, info_as_json

    @classmethod
    def get_driver_name_from_file(self, file_path):
        str_error = ''
        driver_name = ''
        if not isinstance(file_path, str):
            str_error = ('File path must be a string and is a: {}'.format(str(type(file_path))))
            return str_error, driver_name
        if not self.is_initialized:
            str_error = self.initialize()
            if str_error:
                return str_error, driver_name
        file_extension_without_dot = os.path.splitext(file_path)[1][1:]
        if not file_extension_without_dot in self.driver_names_by_file_extension:
            str_error = ('Not found driver for file extension: {}'.format(file_extension_without_dot))
            return str_error, driver_name
        driver_name = self.driver_names_by_file_extension[file_extension_without_dot]
        return str_error, driver_name

    @classmethod
    def get_features(self,
                     file_path,
                     layer_name,
                     fields,
                     filter_fields_or_string= None):
        str_error = ''
        if not isinstance(file_path, str):
            str_error = ('File path must be a string and is a: {}'.format(str(type(file_path))))
            return str_error
        if not self.is_initialized:
            str_error = self.initialize()
            if str_error:
                return str_error
        str_error, is_vector = self.is_vector(file_path)
        if str_error:
            return str_error
        if not is_vector:
            str_error = ('File is not a vector data source:\n{}'.format(file_path))
            return str_error
        features = []
        if not os.path.exists(file_path):
            str_error = ('Not exists file:\n{}'.format(file_path))
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
            ds = ogr.Open(file_path)
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
            str_error = ('Not exists layer: {}\nin file:\n{}'.format(layer_name, file_path))
            return str_error, features
        for field_name in fields:
            field_type = fields[field_name]
            if field_name == defs_gdal.LAYERS_GEOMETRY_TAG:
                if field_type != layer.GetGeomType():
                    str_error = ('In file:\n{}\nin layer: {}\ngeometry type is: {}\ndifferent for selected: {}'.
                                 format(file_path, layer_name, ogr.GeometryTypeToName(layer.GetGeomType()),
                                        ogr.GeometryTypeToName(field_type)))
                    return str_error, features
                continue
            field_idx = layer.GetLayerDefn().GetFieldIndex(field_name)
            if field_idx == -1:
                str_error = ('No field: {} in layer: {}\nin file: {}'.
                             format(field_name, layer_name, file_path))
                return str_error, features
            field_defn = layer.GetLayerDefn().GetFieldDefn(field_idx)
            field_defn_type = field_defn.GetType()
            if field_defn_type != field_type:
                str_error = ('Different type in field: {} in value: {} in layer: {}\nin file:\n{}'.
                             format(field_name, str(i + 1), layer_name, file_path))
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
                                     format(filter_field_name, layer_name, file_path))
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

    @classmethod
    def is_raster(self, file_path):
        str_error = ''
        is_raster = None
        if not self.is_initialized:
            str_error = self.initialize()
            if str_error:
                return str_error, is_raster
        file_extension_without_dot = os.path.splitext(file_path)[1][1:]
        is_raster = file_extension_without_dot in self.raster_drivers_file_extensions
        return str_error, is_raster

    @classmethod
    def is_vector(self, file_path):
        str_error = ''
        is_vector = None
        if not self.is_initialized:
            str_error = self.initialize()
            if str_error:
                return str_error, is_vector
        file_extension_without_dot = os.path.splitext(file_path)[1][1:]
        is_vector = file_extension_without_dot in self.vector_drivers_file_extensions
        return str_error, is_vector

    @classmethod
    def get_layer_field_names(self, file_path, layer_name):
        str_error = ''
        field_names = []
        if not isinstance(file_path, str):
            str_error = ('File path must be a string and is a: {}'.format(str(type(file_path))))
            return str_error, field_names
        if not self.is_initialized:
            str_error = self.initialize()
            if str_error:
                return str_error, field_names
        str_error, is_vector = self.is_vector(file_path)
        if str_error:
            return str_error, field_names
        if not is_vector:
            str_error = ('File is not a vector data source:\n{}'.format(file_path))
            return str_error, field_names
        ds = None
        try:
            ds = ogr.Open(file_path)
        except Exception as e:
            str_error = 'GDAL Error: ' + e.args[0]
            return str_error, field_names
        layer = None
        try:
            layer = ds.GetLayer(layer_name)
        except Exception as e:
            str_error = 'GDAL Error: ' + e.args[0]
            return str_error, field_names
        if not layer:
            str_error = ('Not exists layer: {}\nin file:\n{}'.format(layer_name, file_path))
            return str_error, field_names
        layerDefinition = layer.GetLayerDefn()
        for i in range(layerDefinition.GetFieldCount()):
            field_names.append(layerDefinition.GetFieldDefn(i).GetName())
        return str_error, field_names

    @classmethod
    def get_layer_geometry_type(self, file_path, layer_name):
        str_error = ''
        geometry_type = None
        if not isinstance(file_path, str):
            str_error = ('File path must be a string and is a: {}'.format(str(type(file_path))))
            return str_error, geometry_type
        if not self.is_initialized:
            str_error = self.initialize()
            if str_error:
                return str_error, geometry_type
        if not os.path.exists(file_path):
            str_error = ('Not exists file:\n{}'.format(file_path))
            return str_error, geometry_type
        str_error, is_vector = self.is_vector(file_path)
        if str_error:
            return str_error, geometry_type
        if not is_vector:
            str_error = ('File is not a vector data source:\n{}'.format(file_path))
            return str_error, geometry_type
        ds = None
        try:
            ds = ogr.Open(file_path)
        except Exception as e:
            str_error = 'GDAL Error: ' + e.args[0]
            return str_error, geometry_type
        layer = None
        try:
            layer = ds.GetLayer(layer_name)
        except Exception as e:
            str_error = 'GDAL Error: ' + e.args[0]
            return str_error, geometry_type
        if not layer:
            str_error = ('Not exists layer: {}\nin file:\n{}'.format(layer_name, file_path))
            return str_error, geometry_type
        try:
            geometry_type = layer.GetGeomType()
        except Exception as e:
            str_error = 'GDAL Error: ' + e.args[0]
        return str_error, geometry_type

    @classmethod
    def get_layers_names(self, file_path):
        str_error = ''
        if not isinstance(file_path, str):
            str_error = ('File path must be a string and is a: {}'.format(str(type(file_path))))
            return str_error
        if not self.is_initialized:
            str_error = self.initialize()
            if str_error:
                return str_error
        str_error, is_vector = self.is_vector(file_path)
        if str_error:
            return str_error
        if not is_vector:
            str_error = ('File is not a vector data source:\n{}'.format(file_path))
            return str_error
        layer_names = []
        if not os.path.exists(file_path):
            str_error = ('Not exists file:\n{}'.format(file_path))
            return str_error, layer_names
        try:
            layer_names = [l.GetName() for l in ogr.Open(file_path)]
        except Exception as e:
            str_error = 'GDAL Error: ' + e.args[0]
        return str_error, layer_names

    @classmethod
    def get_metadata(self, file_path, layer_name = None):
        str_error = ''
        info_as_text = ''
        if not isinstance(file_path, str):
            str_error = ('File path must be a string and is a: {}'.format(str(type(file_path))))
            return str_error
        if not self.is_initialized:
            str_error = self.initialize()
            if str_error:
                return str_error
        str_error, is_raster = self.is_raster(file_path)
        if str_error:
            return str_error, info_as_text
        if is_raster:
            str_error, info_as_text = self.gdalinfo_as_json(file_path)
            # try:
            #     alg = gdal.Run("raster", "info", input = file_path) # gdal 3.11
            #     info_as_dict = alg.Output()
            # except Exception as e:
            #     # str_error = 'GDAL Error: ' + e.args[0]
            #     str_error, info_as_dict = self.gdalinfo_as_text(file_path)
        else:
            str_error, info_as_text = self.ogrinfo_as_json(file_path, layer_name)
            # try:
            #     alg = gdal.Run("vector", "info", input = file_path) # gdal 3.11?
            #     info_as_dict = alg.Output()
            # except Exception as e:
            #     # str_error = 'GDAL Error: ' + e.args[0]
            #     str_error, info_as_dict = self.gdalinfo_as_text(file_path)
        return str_error, info_as_text

    @classmethod
    def get_raster_count(self, file_path):
        str_error = ''
        raster_count = -1
        if not isinstance(file_path, str):
            str_error = ('File path must be a string and is a: {}'.format(str(type(file_path))))
            return str_error
        if not self.is_initialized:
            str_error = self.initialize()
            if str_error:
                return str_error
        str_error, is_raster = self.is_raster(file_path)
        if str_error:
            return str_error
        if not is_raster:
            str_error = ('File is not a raster data source:\n{}'.format(file_path))
            return str_error
        ds = None
        try:
            ds = gdal.Open(file_path)
        except Exception as e:
            str_error = 'GDAL Error: ' + e.args[0]
        if ds:
           raster_count = ds.RasterCount
        else:
            str_error = ('File is not a valid raster data source:\n{}'.format(file_path))
            return str_error
        return str_error, raster_count

    @classmethod
    def initialize(self):
        str_error = ''
        self.crs_tools = CRSsTools()
        raster_drivers = []
        vector_drivers = []
        for i in range(gdal.GetDriverCount()):
            drv = gdal.GetDriver(i)
            md = drv.GetMetadata_Dict()
            driver_name = str(drv.ShortName)
            driver_extensions = drv.GetMetadataItem(gdal.DMD_EXTENSIONS)
            if not driver_extensions:
                continue
            driver_extensions = driver_extensions.split()
            # if isinstance(driver_extensions, str):
            #     driver_extensions = [driver_extensions]
            for j in range(len(driver_extensions)):
                driver_extension = driver_extensions[j]
                if not driver_extension in self.driver_names_by_file_extension:
                    self.driver_names_by_file_extension[driver_extension] = []
                if not driver_name in self.driver_names_by_file_extension[driver_extension]:
                    self.driver_names_by_file_extension[driver_extension].append(driver_name)
                if defs_gdal.GDAL_TAG_RASTER in md:
                    if not driver_extension in self.raster_drivers_file_extensions:
                        self.raster_drivers_file_extensions.append(driver_extension)
                if defs_gdal.GDAL_TAG_VECTOR in md:  # note some drivers can handle both raster and vector
                    if not driver_extension in self.vector_drivers_file_extensions:
                        self.vector_drivers_file_extensions.append(driver_extension)
        return str_error

    @classmethod
    def ogrinfo_as_json(self, file_path, layer_name = None): # https://gdal.org/en/stable/programs/gdal_cli_from_python.html, 3.11
        str_error = ''
        info_as_json = ''
        if not isinstance(file_path, str):
            str_error = ('File path must be a string and is a: {}'.format(str(type(file_path))))
            return str_error
        if not self.is_initialized:
            str_error = self.initialize()
            if str_error:
                return str_error, info_as_json
        str_error = ''
        if not isinstance(file_path, str):
            str_error = ('File path must be a string and is a: {}'.format(str(type(file_path))))
            return str_error, info_as_json
        if not self.is_initialized:
            str_error = self.initialize()
            if str_error:
                return str_error, info_as_json
        command = ("ogrinfo -so -json \"{}\"".format(file_path))
        if layer_name:
            command = ("ogrinfo -so -json \"{}\" \"{}\"".format(file_path, layer_name))
        try:
            res = subprocess.Popen(command,
                                   universal_newlines=True,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
            info_as_json, error = res.communicate()
            if error:
                str_error = ('In command:\{}\nError:\n{}'.format(command, error.strip()))
                return str_error, info_as_json
        # except CalledProcessError as e:
        #   print "CalledError > ",e.returncode
        #   print "CalledError > ",e.output
        except OSError as e:
            str_error = ('In command:\{}\nError:\n{}\n{}\n{}'.format(command, e.errno, e.strerror, e.filename))
            return str_error, info_as_json
        except:
            str_error = ('In command:\{}\nError:\n{}'.format(command, sys.exc_info()[0]))
            return str_error, info_as_json
        return str_error, info_as_json

    @classmethod
    def remove_features(self,
                        file_path,
                        features_filter_fields_by_layer):
        # if there are several features for filter all of them will be uptated
        str_error = ''
        if not isinstance(file_path, str):
            str_error = ('File path must be a string and is a: {}'.format(str(type(file_path))))
            return str_error
        if not self.is_initialized:
            str_error = self.initialize()
            if str_error:
                return str_error
        str_error, is_vector = self.is_vector(file_path)
        if str_error:
            return str_error
        if not is_vector:
            str_error = ('File is not a vector data source:\n{}'.format(file_path))
            return str_error
        if not os.path.exists(file_path):
            str_error = ('Not exists file:\n{}'.format(file_path))
            return str_error
        if not isinstance(features_filter_fields_by_layer, dict):
            str_error = ('Features filters by layer argument must be a dictionary of lists')
            return str_error
        for layer_name in features_filter_fields_by_layer:
            if not isinstance(features_filter_fields_by_layer[layer_name], list):
                str_error = ('Features filters by layer argument must be a dictionary of lists')
                return str_error
        # driver = ogr.GetDriverByName("GPKG")
        ds = None
        try:
            ds = ogr.Open(file_path, update = 1)
            # ds = driver.Open(file_path, update = 1)
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
                str_error = ('Not exists layer: {}\nin file:\n{}'.format(layer_name, file_path))
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
                                     format(filter_field_name, layer_name, file_path))
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
                                     format(filter_field_name, str(i + 1), layer_name, file_path))
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

    @classmethod
    def update_features(self,
                        file_path,
                        features_by_layer,
                        features_filter_fields_by_layer):
        # if there are several features for filter all of them will be uptated
        str_error = ''
        if not isinstance(file_path, str):
            str_error = ('File path must be a string and is a: {}'.format(str(type(file_path))))
            return str_error
        if not self.is_initialized:
            str_error = self.initialize()
            if str_error:
                return str_error
        str_error, is_vector = self.is_vector(file_path)
        if str_error:
            return str_error
        if not is_vector:
            str_error = ('File is not a vector data source:\n{}'.format(file_path))
            return str_error
        if not os.path.exists(file_path):
            str_error = ('Not exists file:\n{}'.format(file_path))
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
        # driver = ogr.GetDriverByName("GPKG")
        ds = None
        try:
            ds = ogr.Open(file_path, update = 1)
            # ds = driver.Open(file_path, update = 1)
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
                str_error = ('Not exists layer: {}\nin file:\n{}'.format(layer_name, file_path))
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
                                     format(filter_field_name, layer_name, file_path))
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
                                     format(filter_field_name, str(i + 1), layer_name, file_path))
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
                                         format(field_name, layer_name, file_path))
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
                                         format(str(i+1), layer_name, file_path))
                            return str_error
                    except Exception as e:
                        str_error = 'GDAL Error: ' + e.args[0]
                        return str_error
        return str_error

    @classmethod
    def write_features(self,
                       file_path,
                       features_by_layer):
        str_error = ''
        if not isinstance(file_path, str):
            str_error = ('File path must be a string and is a: {}'.format(str(type(file_path))))
            return str_error
        if not self.is_initialized:
            str_error = self.initialize()
            if str_error:
                return str_error
        str_error, is_vector = self.is_vector(file_path)
        if str_error:
            return str_error
        if not is_vector:
            str_error = ('File is not a vector data source:\n{}'.format(file_path))
            return str_error
        if not os.path.exists(file_path):
            str_error = ('Not exists file:\n{}'.format(file_path))
            return str_error
        if not isinstance(features_by_layer, dict):
            str_error = ('Features by layer argument must be a dictionary of lists')
            return str_error
        for layer_name in features_by_layer:
            if not isinstance(features_by_layer[layer_name], list):
                str_error = ('Features by layer argument must be a dictionary of lists')
                return str_error
        # driver = ogr.GetDriverByName("GPKG")
        ds = None
        try:
            # ds = driver.Open(file_path, update = 1)
            ds = ogr.Open(file_path, update = 1)
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
                str_error = ('Not exists layer: {}\nin file:\n{}'.format(layer_name, file_path))
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
                                     format(field_name, layer_name, file_path))
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
                                     format(str(i+1), layer_name, file_path))
                        return str_error
                except Exception as e:
                    str_error = 'GDAL Error: ' + e.args[0]
                    return str_error
        return str_error