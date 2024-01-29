import re
import os
import shutil
import datetime
import zipfly
import logging
import zipfile
from django.db import connection
from django.http import StreamingHttpResponse
import xml.etree.ElementTree as ET
from rest_framework.reverse import reverse
from rest_framework.generics import GenericAPIView
from django.contrib.sites.models import Site
from django.db.models.expressions import RawSQL
from django.db.models import (
    FilteredRelation,
    Q,
    F,
    Max,
    Exists,
    OuterRef
)
from django.contrib.gis.db.models.functions import AsGeoJSON
from core.models.preferences import SitePreferences
from django.conf import settings
from django.utils import timezone
from georepo.models import (
    EntityId, EntityName, GeographicalEntity,
    DatasetView, DatasetViewResource
)
from georepo.utils.custom_geo_functions import ForcePolygonCCW
from core.settings.utils import absolute_path
from georepo.serializers.entity import ExportGeojsonSerializer
from georepo.utils.renderers import (
    GeojsonRenderer,
    ShapefileRenderer,
    KmlRenderer,
    TopojsonRenderer
)
from georepo.utils.azure_blob_storage import (
    StorageContainerClient,
    AzureStorageZipfly,
    DirectoryClient
)
from georepo.utils.permission import (
    get_view_permission_privacy_level
)
from georepo.utils.entity_query import validate_datetime
from georepo.models.base_task_request import (
    PROCESSING,
    DONE,
    ERROR
)
from georepo.models.export_request import (
    ExportRequest,
    ExportRequestStatusText,
    GEOJSON_EXPORT_TYPE
)
from georepo.utils.tile_configs import (
    get_view_tiling_configs,
    get_admin_level_tiling_config
)


logger = logging.getLogger(__name__)


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
    def __init__(self, request: ExportRequest,
                 is_temp: bool = False,
                 ref = None) -> None:
        self.request = request
        self.is_temp = is_temp
        self.format = self.request.format if not is_temp else 'geojson'
        self.dataset_view = request.dataset_view
        self.total_progress = 0
        self.progress_count = 0
        self.generated_files = []
        self.levels = []
        self.privacy_level = get_view_permission_privacy_level(
            request.submitted_by, self.dataset_view.dataset,
            self.dataset_view
        )
        self.view_resource = DatasetViewResource.objects.filter(
            dataset_view=self.dataset_view,
            privacy_level=self.privacy_level
        ).get()
        self.tiling_configs = []
        self.has_custom_tiling_config = False
        self.exporter_ref = ref

    def get_exported_file_name(self, level: int):
        exported_name = f'adm{level}'
        return exported_name

    def generate_queryset(self):
        entities = GeographicalEntity.objects.filter(
            dataset=self.dataset_view.dataset,
            is_approved=True,
            privacy_level__lte=self.privacy_level
        )
        # raw_sql to view to select id
        raw_sql = (
            'SELECT id from "{}"'
        ).format(str(self.dataset_view.uuid))
        entities = entities.filter(
            id__in=RawSQL(raw_sql, [])
        )
        # do other filters
        if (
            'country' in self.request.filters and
            len(self.request.filters['country']) > 0
        ):
            entities = entities.filter(
                Q(ancestor__label__in=self.request.filters['country']) |
                (
                    Q(ancestor__isnull=True) &
                    Q(label__in=self.request.filters['country'])
                )
            )
        if (
            'privacy_level' in self.request.filters and
            len(self.request.filters['privacy_level']) > 0
        ):
            entities = entities.filter(
                privacy_level__in=self.request.filters['privacy_level']
            )
        if (
            'level' in self.request.filters and
            len(self.request.filters['level']) > 0
        ):
            entities = entities.filter(
                level__in=self.request.filters['level']
            )
        if (
            'admin_level_name' in self.request.filters and
            len(self.request.filters['admin_level_name']) > 0
        ):
            entities = entities.filter(
                admin_level_name__in=self.request.filters['admin_level_name']
            )
        if (
            'type' in self.request.filters and
            len(self.request.filters['type']) > 0
        ):
            entities = entities.filter(
                type__label__in=self.request.filters['type']
            )
        if (
            'revision' in self.request.filters and
            len(self.request.filters['revision']) > 0
        ):
            entities = entities.filter(
                revision_number__in=self.request.filters['revision']
            )
        if (
            'source' in self.request.filters and
            len(self.request.filters['source']) > 0
        ):
            entities = entities.filter(
                source__in=self.request.filters['source']
            )
        if 'valid_from' in self.request.filters:
            valid_from = validate_datetime(self.request.filters['valid_from'])
            if valid_from:
                entities = entities.filter(
                    start_date__lte=valid_from
                )
                entities = entities.filter(
                    Q(end_date__isnull=True) | Q(end_date__gte=valid_from)
                )
        if (
            'search_text' in self.request.filters and
            len(self.request.filters['search_text']) > 0
        ):
            entity_id_qs = EntityId.objects.filter(
                geographical_entity=OuterRef('pk'),
                value__icontains=self.request.filters['search_text']
            )
            entity_name_qs = EntityName.objects.filter(
                geographical_entity=OuterRef('pk'),
                name__icontains=self.request.filters['search_text']
            )
            entities = entities.filter(
                Q(label__icontains=self.request.filters['search_text']) |
                Q(
                    unique_code__icontains=self.request.filters['search_text']
                ) |
                Q(
                    concept_ucode__icontains=(
                        self.request.filters['search_text']
                    )
                ) |
                Q(
                    internal_code__icontains=(
                        self.request.filters['search_text']
                    )
                ) |
                Q(
                    source__icontains=self.request.filters['search_text']
                ) |
                Q(
                    admin_level_name__icontains=(
                        self.request.filters['search_text']
                    )
                ) |
                Q(
                    ancestor__label__icontains=(
                        self.request.filters['search_text']
                    )
                ) |
                Q(Exists(entity_id_qs)) |
                Q(Exists(entity_name_qs))
            )
        return entities

    def init_exporter(self):
        self.total_progress = 0
        self.progress_count = 0
        self.generated_files = []
        self.levels = []
        self.tiling_configs = []
        self.has_custom_tiling_config = False
        if self.request.is_simplified_entities:
            self.tiling_configs, self.has_custom_tiling_config = (
                get_view_tiling_configs(
                    self.request.dataset_view,
                    self.request.simplification_zoom_level
                )
            )
        # check if view at privacy level has data
        entities = self.generate_queryset()
        # count levels
        entity_levels = entities.order_by('level').values_list(
            'level',
            flat=True
        ).distinct()
        for admin_level in entity_levels:
            if self.request.is_simplified_entities:
                # check if this admin level is included in tiling config
                is_included, _ = get_admin_level_tiling_config(
                    admin_level,
                    self.tiling_configs,
                    self.request.simplification_zoom_level
                )
                if is_included:
                    self.levels.append(admin_level)
            else:
                self.levels.append(admin_level)
        self.total_progress = len(self.levels) + 3
        if self.request.format != GEOJSON_EXPORT_TYPE:
            self.total_progress += len(self.levels) + 1
        # update the request status
        self.request.status = PROCESSING
        self.request.started_at = timezone.now()
        self.request.finished_at = None
        self.request.progress = 0
        self.request.errors = None
        self.request.status_text = str(ExportRequestStatusText.RUNNING)
        self.request.save(update_fields=[
            'status', 'status_text', 'started_at',
            'finished_at', 'progress', 'errors'
        ])
        self.update_progress()

    def get_simplification_condition_qs(self, admin_level):
        _, tolerance = get_admin_level_tiling_config(
            admin_level,
            self.tiling_configs,
            self.request.simplification_zoom_level
        )
        if self.has_custom_tiling_config:
            return (
                Q(entitysimplified__simplify_tolerance=tolerance) &
                Q(entitysimplified__dataset_view=self.dataset_view)
            )
        return (
            Q(entitysimplified__simplify_tolerance=tolerance) &
            Q(entitysimplified__dataset_view__isnull=True)
        )

    def get_serializer(self):
        return ExportGeojsonSerializer

    def get_extracted_on(self):
        return (
            self.request.submitted_on if self.request.submitted_on else
            datetime.datetime.now()
        )

    def write_entities(self, entities, context,
                       exported_name, tmp_output_dir,
                       tmp_metadata_file) -> str:
        raise NotImplementedError

    def get_base_output_dir(self) -> str:
        return settings.EXPORT_FOLDER_OUTPUT

    def get_tmp_output_dir(self) -> str:
        tmp_output_dir = os.path.join(
            self.get_base_output_dir(),
            f'temp_{str(self.request.uuid)}'
        )
        if not os.path.exists(tmp_output_dir):
            os.makedirs(tmp_output_dir)
        return tmp_output_dir

    def update_progress(self, inc_progress = 1):
        if self.is_temp:
            if self.exporter_ref:
                self.exporter_ref.update_progress()
            return
        self.progress_count += inc_progress
        self.request.progress = (
            (self.progress_count * 100) / self.total_progress
        ) if self.total_progress > 0 else 0
        self.request.save(update_fields=['progress'])

    def update_progress_text(self, status_text):
        if self.is_temp:
            return
        self.request.status_text = str(status_text)
        self.request.save(update_fields=['status_text'])

    def run(self):
        logger.info(
            f'Exporting {self.format} from View {self.dataset_view.name} '
        )
        tmp_output_dir = self.get_tmp_output_dir()
        # export for each admin level
        for level in self.levels:
            logger.info(
                f'Exporting {self.format} of level {level} from '
                f'{self.dataset_view.name} - {self.privacy_level} '
                f'({self.request.progress} %)'
            )
            self.do_export(level, tmp_output_dir)
            self.update_progress()
        # export readme
        if not self.is_temp:
            self.export_readme(tmp_output_dir)
            self.do_export_post_process()
        logger.info(
            f'Exporting {self.format} is finished '
            f'from {self.dataset_view.name} '
        )
        logger.info(self.generated_files)

    def do_export(self, level: int,
                  tmp_output_dir: str):
        exported_name = self.get_exported_file_name(level)
        entities = self.generate_queryset()
        entities, max_level, ids, names = self.get_dataset_entity_query(
            entities,
            level
        )
        if entities.count() == 0:
            return None
        context = {
            'max_level': max_level,
            'ids': ids,
            'names': names
        }
        # export metadata file
        tmp_metadata_file = self.export_metadata_level(level, tmp_output_dir)
        exported_file_path = self.write_entities(
            entities,
            context,
            exported_name,
            tmp_output_dir,
            tmp_metadata_file
        )
        if exported_file_path and os.path.exists(exported_file_path):
            self.generated_files.append(exported_file_path)
        else:
            logger.error(f'Failed to generate {self.format} at level {level}')

    def get_dataset_entity_query(self, entities, level: int):
        # initial fields to select
        values = [
            'id', 'label', 'internal_code',
            'unique_code', 'unique_code_version',
            'uuid', 'uuid_revision',
            'type__label', 'level', 'start_date', 'end_date',
            'is_latest', 'admin_level_name'
        ]
        entities = entities.filter(
            level=level
        )
        geom_field = 'geometry'
        if self.request.is_simplified_entities:
            entities = entities.annotate(
                simplified=FilteredRelation(
                    'entitysimplified',
                    condition=self.get_simplification_condition_qs(level)
                )
            )
            entities = entities.exclude(
                simplified__simplified_geometry__isnull=True
            )
            geom_field = 'simplified__simplified_geometry'
        entities = entities.annotate(
            rhr_geom=AsGeoJSON(ForcePolygonCCW(F(geom_field)))
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
        # raw_sql to view to select id
        raw_sql = (
            'SELECT id from "{}"'
        ).format(str(self.dataset_view.uuid))
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

    def export_readme(self, tmp_output_dir: str):
        logger.info('Generating readme file')
        dataset = self.dataset_view.dataset
        simplification_zoom_level = (
            str(self.request.simplification_zoom_level) if
            self.request.is_simplified_entities else '-'
        )
        lines = [
            'Readme',
            f'Dataset: {dataset.label}',
            f'Description: {dataset.description}',
            f"Extracted on {self.get_extracted_on().strftime('%d-%m-%Y')}"
            '',
            f'View: {self.dataset_view.name}',
            f'View Description: {self.dataset_view.description}',
            f'View UUID: {self.dataset_view.uuid}',
            f'View Query: {self.dataset_view.query_string}',
            '',
            f'Is Simplified Entities: {self.request.is_simplified_entities}',
            f'Simplification Zoom Level: {simplification_zoom_level}',
        ]
        if self.request.filters:
            lines.append('Filters:')
            for key, value in self.request.filters.items():
                lines.append(f'{key}: {str(value)}')
        else:
            lines.append('Filters: -')
        lines.append('')
        readme_filepath = os.path.join(
            tmp_output_dir,
            'readme.txt'
        )
        with open(readme_filepath, 'w') as f:
            for line in lines:
                f.write(line)
                f.write('\n')
        self.generated_files.append(readme_filepath)

    def export_metadata(self, tmp_output_dir: str):
        logger.info('Generating metadata file')
        dataset = self.dataset_view.dataset
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
            entities = self.generate_queryset()
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
            f"Extracted on {self.get_extracted_on().strftime('%d-%m-%Y')}"
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
        xml_el.text = self.get_extracted_on().isoformat()
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

    def do_export_post_process(self):
        if self.is_temp:
            return
        self.update_progress_text(
            ExportRequestStatusText.CREATING_ZIP_ARCHIVE
        )
        tmp_output_dir = self.get_tmp_output_dir()
        # zip all files inside generated_files
        zip_file_path = os.path.join(
            tmp_output_dir,
            f'{self.dataset_view.name}'
        ) + '.zip'
        with zipfile.ZipFile(
                zip_file_path, 'w', zipfile.ZIP_DEFLATED) as archive:
            for result_file in self.generated_files:
                archive.write(
                    result_file,
                    arcname=os.path.basename(result_file)
                )
        with open(zip_file_path, 'rb') as zip_file:
            self.request.output_file.save(
                os.path.basename(zip_file_path),
                zip_file
            )
        self.do_remove_temp_dir()
        self.update_progress()
        # generate download link and expiry
        expired_on = (
            timezone.now() +
            datetime.timedelta(hours=settings.EXPORT_DATA_EXPIRY_IN_HOURS)
        )
        download_link = None
        if settings.USE_AZURE:
            file_path = f'media/{self.request.output_file.name}'
            bc = StorageContainerClient.get_blob_client(blob=file_path)
            if bc.exists():
                # generate temporary url with sas token
                client = DirectoryClient(settings.AZURE_STORAGE,
                                         settings.AZURE_STORAGE_CONTAINER)
                download_link = client.generate_url_for_file(
                    file_path, settings.EXPORT_DATA_EXPIRY_IN_HOURS)
            else:
                expired_on = None
        else:
            current_site = Site.objects.get_current()
            scheme = 'https://'
            download_link = (
                f'{scheme}{current_site.domain}{self.request.output_file.url}'
            )
        self.request.download_link_expired_on = expired_on
        self.request.download_link = download_link
        is_success = download_link is not None
        if is_success:
            self.request.status = DONE
            self.request.status_text = str(ExportRequestStatusText.READY)
            self.request.errors = None
        else:
            self.request.status = ERROR
            self.request.status_text = str(ExportRequestStatusText.ABORTED)
            self.request.errors = (
                'Unable to generate download link for the zip archive!'
            )
        self.request.finished_at = timezone.now()
        self.request.progress = 100
        self.request.save(
            update_fields=[
                'download_link', 'download_link_expired_on', 'status',
                'status_text', 'errors', 'finished_at', 'progress'
            ]
        )

    def do_remove_temp_dir(self):
        tmp_output_dir = self.get_tmp_output_dir()
        if os.path.exists(tmp_output_dir):
            shutil.rmtree(tmp_output_dir)


class APIDownloaderBase(GenericAPIView):
    """!DEPRECATED! Base class for download view."""
    renderer_classes = [
        GeojsonRenderer,
        ShapefileRenderer,
        KmlRenderer,
        TopojsonRenderer
    ]

    def get_output_format(self):
        output = {}
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
        paths = []
        for result in result_list:
            file_name = result.split('/')[-1]
            if 'readme' in file_name:
                item_file_name = file_name
            else:
                item_file_name = f'{prefix_name} {file_name}'
            paths.append({
                'fs': result,
                'n': item_file_name
            })
        zfly = None
        if settings.USE_AZURE:
            zfly = AzureStorageZipfly(
                paths=paths, storage_container_client=StorageContainerClient)
        else:
            zfly = zipfly.ZipFly(paths=paths)
        z = zfly.generator()
        response = StreamingHttpResponse(
            z, content_type='application/octet-stream')
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
