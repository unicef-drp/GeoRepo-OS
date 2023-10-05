import re
import math
import os
import shutil
import datetime
import tempfile
import zipfile
from django.db import connection
from django.http import HttpResponse
import xml.etree.ElementTree as ET
from collections import OrderedDict
from rest_framework.reverse import reverse
from rest_framework.generics import GenericAPIView
from django.contrib.sites.models import Site
from django.db.models.expressions import RawSQL
from django.db.models import FilteredRelation, Q, F, Max
from django.contrib.gis.geos import GEOSGeometry
from django.contrib.gis.db.models.functions import AsGeoJSON
from core.models.preferences import SitePreferences
from django.conf import settings
from georepo.models import (
    EntityId, EntityName, GeographicalEntity,
    DatasetView, DatasetViewResource
)
from georepo.utils.custom_geo_functions import ForcePolygonCCW
from core.settings.utils import absolute_path
from georepo.serializers.entity import ExportGeojsonSerializer
from georepo.utils.dataset_view import (
    check_view_exists,
    create_sql_view,
    get_entities_count_in_view
)
from georepo.utils.renderers import (
    GeojsonRenderer,
    ShapefileRenderer,
    KmlRenderer,
    TopojsonRenderer
)
from georepo.utils.azure_blob_storage import (
    DirectoryClient,
    StorageContainerClient
)
from georepo.utils.directory_helper import (
    get_folder_size
)

PROPERTY_INT_VALUES = ['admin_level']
PROPERTY_BOOL_VALUES = ['is_latest']
METADATA_TEMPLATE_PATH = absolute_path(
    'georepo', 'utils', 'metadata_template.xml'
)


def get_property_type(property: str):
    for val in PROPERTY_BOOL_VALUES:
        if val in property:
            return 'bool'
    for val in PROPERTY_INT_VALUES:
        if val in property:
            return 'int'
    return 'str'


def get_dataset_exported_file_name(level: int,
                                   adm0: GeographicalEntity = None):
    exported_name = f'all_adm{level}'
    if adm0:
        exported_name = f'{adm0.unique_code}_adm{level}'
    return exported_name


class DatasetViewExporterBase(object):
    output = None

    def __init__(self, dataset_view: DatasetView,
                 view_resource: DatasetViewResource = None) -> None:
        self.dataset_view = dataset_view
        self.total_to_be_exported = 0
        self.total_exported = 0
        self.generated_files = []
        self.resources = []
        self.view_resource = view_resource

    def get_exported_file_name(self, level: int):
        exported_name = f'adm{level}'
        return exported_name

    def init_exporter(self):
        self.total_to_be_exported = 0
        resources = DatasetViewResource.objects.filter(
            dataset_view=self.dataset_view
        ).order_by('privacy_level')
        if self.view_resource:
            resources = resources.filter(
                id=self.view_resource.id
            )
        for resource in resources:
            # check entities count in current privacy level
            entity_count = get_entities_count_in_view(
                self.dataset_view,
                resource.privacy_level
            )
            # skip generation if no entity at current level
            if entity_count == 0:
                continue
            # check if view at privacy level has data
            entities = GeographicalEntity.objects.filter(
                dataset=self.dataset_view.dataset,
                is_approved=True,
                privacy_level__lte=resource.privacy_level
            )
            # raw_sql to view to select id
            raw_sql = (
                'SELECT id from "{}"'
            ).format(str(self.dataset_view.uuid))
            entities = entities.filter(
                id__in=RawSQL(raw_sql, [])
            )
            if not entities.exists():
                continue
            # count levels
            levels = entities.order_by('level').values_list(
                'level',
                flat=True
            ).distinct()
            self.resources.append({
                'resource': resource,
                'levels': levels
            })
            self.total_to_be_exported += len(levels)

        self.countries = {}
        self.total_exported = 0
        self.generated_files = []

    def get_serializer(self):
        return ExportGeojsonSerializer

    def write_entities(self, schema, entities, context,
                       exported_name, tmp_output_dir,
                       tmp_metadata_file, resource) -> str:
        raise NotImplementedError

    def get_base_output_dir(self) -> str:
        raise NotImplementedError

    def get_tmp_output_dir(self, resource: DatasetViewResource) -> str:
        tmp_output_dir = os.path.join(
            self.get_base_output_dir(),
            f'temp_{str(resource.uuid)}'
        )
        if not os.path.exists(tmp_output_dir):
            os.makedirs(tmp_output_dir)
        return tmp_output_dir

    def update_progress(self, view_resource=None, progress=0):
        view_resource = view_resource['resource'] if \
            view_resource else \
            self.view_resource
        setattr(view_resource, f'{self.output}_progress', progress)
        if math.isclose(progress, 100, abs_tol=1e-4):
            setattr(
                view_resource,
                f'{self.output}_sync_status',
                DatasetViewResource.SyncStatus.SYNCED
            )
            output_path = self.get_tmp_output_dir(view_resource)
            setattr(
                view_resource,
                f'{self.output}_size',
                get_folder_size(output_path)
            )
        view_resource.save()

    def run(self):
        print(
            f'Exporting {self.output} from View {self.dataset_view.name} '
            f'(0/{self.total_to_be_exported})'
        )
        # check if view has been created
        is_view_exists = check_view_exists(str(self.dataset_view.uuid))
        if not is_view_exists:
            create_sql_view(self.dataset_view)

        for res in self.resources:
            resource = res['resource']
            levels = res['levels']
            tmp_output_dir = self.get_tmp_output_dir(resource)
            # export for each admin level
            for level in levels:
                print(
                    f'Exporting {self.output} of level {level} from '
                    f'{self.dataset_view.name} - {resource.privacy_level} '
                    f'({self.total_exported}/{self.total_to_be_exported})'
                )
                self.do_export(resource, resource.privacy_level,
                               level, tmp_output_dir)
                self.total_exported += 1
                self.update_progress(
                    res,
                    (self.total_exported / self.total_to_be_exported) * 100
                )
            # export readme
            self.export_readme(tmp_output_dir)
            self.do_export_post_process(resource)
        print(
            f'Exporting {self.output} is finished '
            f'from {self.dataset_view.name} '
            f'({self.total_exported}/{self.total_to_be_exported})'
        )
        print(self.generated_files)

    def do_export(self, resource, privacy_level: int, level: int,
                  tmp_output_dir: str):
        exported_name = self.get_exported_file_name(level)
        entities, max_level, ids, names = self.get_dataset_entity_query(
            privacy_level,
            level=level
        )
        if entities.count() == 0:
            return None
        context = {
            'max_level': max_level,
            'ids': ids,
            'names': names
        }
        first_entity = entities.first()
        schema = self.get_schema(first_entity, context)
        # export metadata file
        tmp_metadata_file = self.export_metadata_level(level, tmp_output_dir)
        exported_file_path = self.write_entities(
            schema,
            entities,
            context,
            exported_name,
            tmp_output_dir,
            tmp_metadata_file,
            resource
        )
        if exported_file_path:
            self.generated_files.append(exported_file_path)

    def get_dataset_entity_query(self, privacy_level: int, level: int = None):
        # initial fields to select
        values = [
            'id', 'label', 'internal_code',
            'unique_code', 'unique_code_version',
            'uuid', 'uuid_revision',
            'type__label', 'level', 'start_date', 'end_date',
            'is_latest', 'admin_level_name'
        ]
        entities = GeographicalEntity.objects.filter(
            dataset=self.dataset_view.dataset,
            is_approved=True,
            privacy_level__lte=privacy_level
        )
        # raw_sql to view to select id
        raw_sql = (
            'SELECT id from "{}"'
        ).format(str(self.dataset_view.uuid))
        entities = entities.filter(
            id__in=RawSQL(raw_sql, [])
        )
        if level is not None:
            entities = entities.filter(
                level=level
            )
        entities = entities.annotate(
            rhr_geom=AsGeoJSON(ForcePolygonCCW(F('geometry')))
        )
        values.append('rhr_geom')
        # get max levels
        max_level = 0
        max_level_entity = entities.order_by(
                'level'
        ).last()
        if max_level_entity:
            max_level = max_level_entity.level
        related = ''
        for i in range(max_level):
            related = related + (
                '__parent' if i > 0 else 'parent'
            )
            # fetch parent's default code
            values.append(f'{related}__internal_code')
            values.append(f'{related}__unique_code')
            values.append(f'{related}__unique_code_version')
            values.append(f'{related}__level')
            values.append(f'{related}__type__label')
        # retrieve all ids in current dataset
        ids = EntityId.objects.filter(
            geographical_entity__dataset__id=self.dataset_view.dataset.id,
            geographical_entity__is_approved=True,
            geographical_entity__level=level
        )
        ids = ids.filter(
            geographical_entity__id__in=RawSQL(raw_sql, [])
        )
        ids = ids.order_by('code').values(
            'code__id', 'code__name', 'default'
        ).distinct('code__id')
        # conditional join to entity id for each id
        for id in ids:
            field_key = f"id_{id['code__id']}"
            annotations = {
                field_key: FilteredRelation(
                    'entity_ids',
                    condition=Q(entity_ids__code__id=id['code__id'])
                )
            }
            entities = entities.annotate(**annotations)
            values.append(f'{field_key}__value')
        names = EntityName.objects.filter(
            geographical_entity__dataset__id=self.dataset_view.dataset.id,
            geographical_entity__is_approved=True,
            geographical_entity__level=level
        )
        names = names.filter(
            geographical_entity__id__in=RawSQL(raw_sql, [])
        )
        # get max idx in the names
        names_max_idx = names.aggregate(
            Max('idx')
        )
        if names_max_idx['idx__max'] is not None:
            for name_idx in range(names_max_idx['idx__max'] + 1):
                field_key = f"name_{name_idx}"
                annotations = {
                    field_key: FilteredRelation(
                        'entity_names',
                        condition=Q(
                            entity_names__idx=name_idx
                        )
                    )
                }
                entities = entities.annotate(**annotations)
                values.append(f'{field_key}__name')
                values.append(f'{field_key}__language__code')
                values.append(f'{field_key}__label')
        entities = entities.values(*values)
        return entities, max_level, ids, names_max_idx

    def get_schema(self, entity: GeographicalEntity, context):
        # NOTE: if the shapefile includes all version,
        # then need to use entity at lowest level to get complete schema
        data = self.get_serializer()(
            entity,
            many=False,
            context=context
        ).data
        properties = []
        for property in data['properties']:
            properties.append((property, get_property_type(property)))
        geometry = GEOSGeometry(entity['rhr_geom'])
        schema = {
            'geometry': geometry.geom_type,
            'properties': OrderedDict(properties)
        }
        return schema

    def export_readme(self, tmp_output_dir: str):
        print('Generating readme file')
        dataset = self.dataset_view.dataset
        extracted_on = datetime.datetime.now()
        lines = [
            'Readme',
            f'Dataset: {dataset.label}',
            f'Description: {dataset.description}',
            '',
            f'View: {self.dataset_view.name}',
            f'View Description: {self.dataset_view.description}',
            f'View UUID: {self.dataset_view.uuid}',
            f'View Query: {self.dataset_view.query_string}',
            '',
            f"Extracted on {extracted_on.strftime('%d-%m-%Y')}"
        ]
        readme_filepath = os.path.join(
            tmp_output_dir,
            'readme.txt'
        )
        with open(readme_filepath, 'w') as f:
            for line in lines:
                f.write(line)
                f.write('\n')

    def export_metadata(self, tmp_output_dir: str):
        print('Generating metadata file')
        dataset = self.dataset_view.dataset
        extracted_on = datetime.datetime.now()
        dataset_desc = (
            dataset.description if dataset.description else '-'
        )
        lines = [
            f'Dataset: {dataset.label}',
            f'Description: {dataset_desc}'
        ]
        if (
            self.dataset_view.default_ancestor_code and
            self.dataset_view.default_type ==
            DatasetView.DefaultViewType.IS_LATEST
        ):
            # find versions in the dataset
            entities = GeographicalEntity.objects.filter(
                dataset=dataset,
                is_approved=True
            )
            # raw_sql to view to select id
            raw_sql = (
                'SELECT id from "{}"'
            ).format(str(self.dataset_view.uuid))
            entities = entities.filter(
                id__in=RawSQL(raw_sql, [])
            )
            revisions = entities.order_by('unique_code_version').values_list(
                'unique_code_version',
                flat=True
            ).distinct()
            if revisions and len(revisions) == 1:
                lines.append(f'Version: {revisions[0]}')
        lines.append(f'UUID: {dataset.uuid}')
        view_desc = (
            self.dataset_view.description if
            self.dataset_view.description else '-'
        )
        lines.extend([
            '',
            f'View: {self.dataset_view.name}',
            f'Description: {view_desc}',
            f'UUID: {self.dataset_view.uuid}',
            f'Query: {self.dataset_view.query_string}',
            '',
            f"Extracted on {extracted_on.strftime('%d-%m-%Y')}"
        ])
        metadata_filepath = os.path.join(
            tmp_output_dir,
            'metadata.txt'
        )
        with open(metadata_filepath, 'w') as f:
            for line in lines:
                f.write(line)
                f.write('\n')

    def export_metadata_level(self, level, tmp_output_dir: str):
        adm_name = self.get_exported_file_name(level)
        view_name = f'{self.dataset_view.name} - {adm_name}'
        # read xml template
        tree = ET.parse(METADATA_TEMPLATE_PATH)
        root = tree.getroot()
        nsmap = {
            'gml': 'http://www.opengis.net/gml',
            'gmd': 'http://www.isotc211.org/2005/gmd',
            'gco': 'http://www.isotc211.org/2005/gco'
        }
        for key in nsmap:
            ET.register_namespace(key, nsmap[key])
        # read configs
        config = SitePreferences.preferences().metadata_xml_config
        apiLatestVersion = SitePreferences.preferences().api_latest_version
        # replace view uuid
        xml_path = 'gmd:fileIdentifier/gco:CharacterString'
        xml_el = root.find(xml_path, nsmap)
        xml_el.text = str(self.dataset_view.uuid)
        # replace contact name
        xml_path = (
            './/gmd:CI_ResponsibleParty/gmd:individualName/gco:CharacterString'
        )
        for name in root.findall(xml_path, nsmap):
            name.text = config['ContactName']
        # replace contact org
        xml_path = (
            './/gmd:CI_ResponsibleParty/gmd:organisationName/'
            'gco:CharacterString'
        )
        for org in root.findall(xml_path, nsmap):
            org.text = config['ContactOrg']
        # replace contact position
        xml_path = (
            './/gmd:CI_ResponsibleParty/gmd:positionName/gco:CharacterString'
        )
        for org in root.findall(xml_path, nsmap):
            org.text = config['ContactPosition']
        # replace License
        xml_path = (
            'gmd:identificationInfo/'
            'gmd:MD_DataIdentification/gmd:resourceConstraints/'
            'gmd:MD_LegalConstraints/gmd:otherConstraints/gco:CharacterString'
        )
        xml_el = root.find(xml_path, nsmap)
        xml_el.text = config['License']
        # replace date time
        xml_path = (
            'gmd:dateStamp/gco:DateTime'
        )
        xml_el = root.find(xml_path, nsmap)
        xml_el.text = datetime.datetime.now().isoformat()
        # replace view name
        xml_path = (
            'gmd:identificationInfo/'
            'gmd:MD_DataIdentification/gmd:citation/'
            'gmd:CI_Citation/gmd:title/gco:CharacterString'
        )
        xml_el = root.find(xml_path, nsmap)
        xml_el.text = view_name
        # replace view desc
        xml_path = (
            'gmd:identificationInfo/'
            'gmd:MD_DataIdentification/gmd:abstract/gco:CharacterString'
        )
        xml_el = root.find(xml_path, nsmap)
        view_desc = (
            self.dataset_view.description + '\r\n' if
            self.dataset_view.description else ''
        )
        xml_el.text = (
            view_desc +
            'Query: ' + '\r\n' +
            self.dataset_view.query_string
        )
        # replace distribution URL
        xml_path = (
            'gmd:distributionInfo/gmd:MD_Distribution/'
            'gmd:transferOptions/gmd:MD_DigitalTransferOptions/gmd:onLine/'
            'gmd:CI_OnlineResource/gmd:linkage/gmd:URL'
        )
        xml_el = root.find(xml_path, nsmap)
        current_site = Site.objects.get_current()
        scheme = 'https://'
        url = reverse(
            f'{apiLatestVersion}:search-view-entity-by-level',
            kwargs={
                'uuid': str(self.dataset_view.uuid),
                'admin_level': level
            }
        )
        xml_el.text = (
            f'{scheme}{current_site.domain}{url}'
        )
        # replace distribution view name
        xml_path = (
            'gmd:distributionInfo/gmd:MD_Distribution/'
            'gmd:transferOptions/gmd:MD_DigitalTransferOptions/gmd:onLine/'
            'gmd:CI_OnlineResource/gmd:name/gco:CharacterString'
        )
        xml_el = root.find(xml_path, nsmap)
        xml_el.text = view_name
        # replace distribution desc
        xml_path = (
            'gmd:distributionInfo/gmd:MD_Distribution/'
            'gmd:transferOptions/gmd:MD_DigitalTransferOptions/gmd:onLine/'
            'gmd:CI_OnlineResource/gmd:description/gco:CharacterString'
        )
        xml_el = root.find(xml_path, nsmap)
        xml_el.text = f'URL to {view_name}'
        # replace bbox if exists in view
        bbox = []
        if self.dataset_view.bbox:
            _bbox = self.dataset_view.bbox.split(',')
            for coord in _bbox:
                bbox.append(str(round(float(coord), 5)))
        else:
            with connection.cursor() as cursor:
                sql_view = str(self.dataset_view.uuid)
                cursor.execute(
                    f'SELECT ST_Extent(geometry) as bextent FROM "{sql_view}"'
                )
                extent = cursor.fetchone()
                if extent:
                    try:
                        _bbox = (
                            re.findall(r'[-+]?(?:\d*\.\d+|\d+)', extent[0])
                        )
                        for coord in _bbox:
                            bbox.append(str(round(float(coord), 5)))
                    except TypeError:
                        pass
        if bbox:
            # write bbox (west, south, east, north)
            xml_path = (
                'gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/'
                'gmd:EX_Extent/gmd:geographicElement/'
                'gmd:EX_GeographicBoundingBox/'
                'gmd:westBoundLongitude/gco:Decimal'
            )
            xml_el = root.find(xml_path, nsmap)
            xml_el.text = bbox[0]
            xml_path = (
                'gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/'
                'gmd:EX_Extent/gmd:geographicElement/'
                'gmd:EX_GeographicBoundingBox/'
                'gmd:southBoundLatitude/gco:Decimal'
            )
            xml_el = root.find(xml_path, nsmap)
            xml_el.text = bbox[1]
            xml_path = (
                'gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/'
                'gmd:EX_Extent/gmd:geographicElement/'
                'gmd:EX_GeographicBoundingBox/'
                'gmd:eastBoundLongitude/gco:Decimal'
            )
            xml_el = root.find(xml_path, nsmap)
            xml_el.text = bbox[2]
            xml_path = (
                'gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/'
                'gmd:EX_Extent/gmd:geographicElement/'
                'gmd:EX_GeographicBoundingBox/'
                'gmd:northBoundLatitude/gco:Decimal'
            )
            xml_el = root.find(xml_path, nsmap)
            xml_el.text = bbox[3]
        # write to output dir
        metadata_filepath = os.path.join(
            tmp_output_dir,
            f'{adm_name}.xml'
        )
        tree.write(metadata_filepath,
                   xml_declaration=True,
                   encoding='utf-8',
                   method="xml")
        # return template file path
        return metadata_filepath

    def do_export_post_process(self, resource: DatasetViewResource):
        tmp_output_dir = os.path.join(
            self.get_base_output_dir(),
            f'temp_{str(resource.uuid)}'
        )
        if settings.USE_AZURE:
            output_dir = (
                f'media/export_data/{self.output}/'
                f'{str(resource.uuid)}'
            )
            client = DirectoryClient(settings.AZURE_STORAGE,
                                     settings.AZURE_STORAGE_CONTAINER)
            client.rmdir(output_dir)
            client.upload_dir(tmp_output_dir, output_dir)
            if self.output != 'geojson':
                self.do_remove_temp_dir(resource)
        else:
            # copy from temp dir to output dir
            output_dir = os.path.join(
                self.get_base_output_dir(),
                str(resource.uuid)
            )
            if os.path.exists(output_dir):
                shutil.rmtree(output_dir)
            try:
                shutil.move(
                    tmp_output_dir,
                    output_dir
                )
            except FileNotFoundError as ex:
                print(ex)

    def do_remove_temp_dir(self, resource: DatasetViewResource):
        tmp_output_dir = os.path.join(
            self.get_base_output_dir(),
            f'temp_{str(resource.uuid)}'
        )
        if os.path.exists(tmp_output_dir):
            shutil.rmtree(tmp_output_dir)

    def do_remove_temp_dirs(self):
        for res in self.resources:
            resource = res['resource']
            self.do_remove_temp_dir(resource)

    def get_geojson_reference_file(self, resource: DatasetViewResource,
                                   exported_name: str):
        res_name = str(resource.uuid)
        if settings.USE_AZURE:
            res_name = f'temp_{str(resource.uuid)}'
        file_path = os.path.join(
            settings.GEOJSON_FOLDER_OUTPUT,
            res_name,
            exported_name
        ) + '.geojson'
        return file_path


class APIDownloaderBase(GenericAPIView):
    """Base class for download view."""
    renderer_classes = [
        GeojsonRenderer,
        ShapefileRenderer,
        KmlRenderer,
        TopojsonRenderer
    ]

    def get_output_format(self):
        output = {}
        format = self.request.GET.get('format', 'geojson')
        if format == 'geojson':
            output = {
                'suffix': '.geojson',
                'directory': (
                    settings.GEOJSON_FOLDER_OUTPUT if
                    not settings.USE_AZURE else
                    'media/export_data/geojson/'
                )
            }
        elif format == 'shapefile':
            output = {
                'suffix': '.zip',
                'directory': (
                    settings.SHAPEFILE_FOLDER_OUTPUT if
                    not settings.USE_AZURE else
                    'media/export_data/shapefile/'
                )
            }
        elif format == 'kml':
            output = {
                'suffix': '.kml',
                'directory': (
                    settings.KML_FOLDER_OUTPUT if
                    not settings.USE_AZURE else
                    'media/export_data/kml/'
                )
            }
        elif format == 'topojson':
            output = {
                'suffix': '.topojson',
                'directory': (
                    settings.TOPOJSON_FOLDER_OUTPUT if
                    not settings.USE_AZURE else
                    'media/export_data/topojson/'
                )
            }
        return output

    def append_readme(self, resource: DatasetViewResource,
                      output_format, results):
        # add readme
        file_path = self.get_resource_path(
            output_format['directory'],
            resource,
            'readme.txt',
            ''
        )
        if self.check_exists(file_path):
            results.append(file_path)

    def get_output_names(self, dataset_view: DatasetView):
        prefix_name = dataset_view.name
        zip_file_name = f'{prefix_name}.zip'
        return prefix_name, zip_file_name

    def prepare_response(self, prefix_name, zip_file_name, result_list):
        with tempfile.SpooledTemporaryFile() as tmp_file:
            with zipfile.ZipFile(
                    tmp_file, 'w', zipfile.ZIP_DEFLATED) as archive:
                for result in result_list:
                    file_name = result.split('/')[-1]
                    if 'readme' in file_name:
                        item_file_name = file_name
                    else:
                        item_file_name = f'{prefix_name} {file_name}'
                    if settings.USE_AZURE:
                        if StorageContainerClient:
                            bc = StorageContainerClient.get_blob_client(
                                blob=result)
                            download_stream = bc.download_blob(
                                max_concurrency=2,
                                validate_content=False
                            )
                            archive.writestr(item_file_name,
                                             download_stream.readall())
                    else:
                        archive.write(
                            result,
                            arcname=item_file_name
                        )
            tmp_file.seek(0)
            response = HttpResponse(
                tmp_file.read(), content_type='application/x-zip-compressed'
            )
            response['Content-Disposition'] = (
                'attachment; filename="{}"'.format(
                    zip_file_name
                )
            )
            return response

    def check_exists(self, file_path):
        if settings.USE_AZURE:
            if StorageContainerClient:
                bc = StorageContainerClient.get_blob_client(blob=file_path)
                return bc.exists()
            else:
                raise RuntimeError('Invalid Azure Storage Container')
        else:
            return os.path.exists(file_path)

    def get_resource_path(self, base_dir, resource: DatasetViewResource,
                          exported_name, file_suffix):
        if settings.USE_AZURE:
            if not base_dir.endswith('/'):
                base_dir += '/'
            return (
                f'{base_dir}{str(resource.uuid)}/'
                f'{exported_name}{file_suffix}'
            )
        return os.path.join(
            base_dir,
            str(resource.uuid),
            exported_name
        ) + file_suffix
