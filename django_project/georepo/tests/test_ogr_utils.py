from django.test import TestCase
from georepo.utils.ogr_utils import parse_ogrinfo_output


class TestOgrUtils(TestCase):

    def test_parse_ogrinfo_output(self):
        output = (
            'INFO: Open of `/vsizip/Global_bnd_adm1_WFP_fixed.zip\'\n'
            '    using driver `ESRI Shapefile\' successful.\n'
            '\n'
            'Layer name: Global_bnd_adm1_WFP_fixed_20230601\n'
            'Metadata:\n'
            'DBF_DATE_LAST_UPDATE=2023-06-01\n'
            'Geometry: Polygon\n'
            'Feature Count: 3485\n'
            'Extent: (-180.000005, -89.900002) - (180.000029, 83.627419)\n'
            'Layer SRS WKT:\n'
            'GEOGCRS["WGS 84",\n'
            '    DATUM["World Geodetic System 1984",\n'
            '        ELLIPSOID["WGS 84",6378137,298.257223563,\n'
            '            LENGTHUNIT["metre",1]]],\n'
            '    PRIMEM["Greenwich",0,\n'
            '        ANGLEUNIT["degree",0.0174532925199433]],\n'
            '    CS[ellipsoidal,2],\n'
            '        AXIS["latitude",north,\n'
            '            ORDER[1],\n'
            '            ANGLEUNIT["degree",0.0174532925199433]],\n'
            '        AXIS["longitude",east,\n'
            '            ORDER[2],\n'
            '            ANGLEUNIT["degree",0.0174532925199433]],\n'
            '    ID["EPSG",4326]]\n'
            'Data axis to CRS axis mapping: 2,1\n'
            'OBJECTID: Integer64 (10.0)\n'
            'iso3: String (3.0)\n'
            'adm1_name: String (70.0)\n'
            'adm1_altnm: String (100.0)\n'
            'adm1_id: Integer64 (10.0)\n'
            'adm0_name: String (70.0)\n'
            'adm0_id: Integer (5.0)\n'
            'mapclr: String (3.0)\n'
            'rb: String (3.0)\n'
            'disp_area: String (3.0)\n'
            'salb_id: String (7.0)\n'
            'source: String (35.0)\n'
            'source_id: String (15.0)\n'
            'source_dat: Date (10.0)\n'
            'lst_update: Date (10.0)\n'
            'validity: Integer (5.0)\n'
            'shape_Leng: Real (19.11)\n'
            'shape_Area: Real (19.11)\n'
        )
        feature_count, is_crs_4326, attributes = parse_ogrinfo_output(output)
        self.assertTrue(is_crs_4326)
        self.assertEqual(feature_count, 3485)
        self.assertEqual(len(attributes), 18)
        self.assertIn('source_id', attributes)
