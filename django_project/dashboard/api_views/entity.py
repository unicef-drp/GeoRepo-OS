import csv
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.utils import timezone
from guardian.core import ObjectPermissionChecker
from rest_framework import serializers
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from guardian.shortcuts import get_objects_for_user
from dashboard.models import (
    EntityUploadStatus,
    BatchEntityEdit
)
from georepo.models import (
    GeographicalEntity,
    Dataset,
    DatasetView
)
from georepo.models.base_task_request import COMPLETED_STATUS, PENDING, DONE
from georepo.tasks.dataset_view import check_affected_dataset_views
from georepo.utils.permission import (
    EXTERNAL_READ_VIEW_PERMISSION_LIST,
    get_view_permission_privacy_level,
    get_external_view_permission_privacy_level
)
from dashboard.serializers.entity import (
    EntityConceptUCodeSerializer,
    EntityEditSerializer,
    BatchEntityEditSerializer
)
from dashboard.tools.entity_edit import (
    try_delete_uploaded_file,
    get_entity_edit_importer
)
from dashboard.tasks.batch_edit import process_batch_entity_edit
from georepo.utils.celery_helper import cancel_task


class EntityRevisionSerializer(serializers.ModelSerializer):
    revision = serializers.SerializerMethodField()
    date = serializers.SerializerMethodField()
    reviewable = serializers.SerializerMethodField()
    uploader = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    def get_date(self, obj: GeographicalEntity):
        if obj.approved_date:
            return obj.approved_date
        if obj.start_date:
            return obj.start_date
        return ''

    def get_status(self, obj: GeographicalEntity):
        if obj.is_approved:
            return 'Approved'
        return 'Pending'

    def get_uploader(self, obj: GeographicalEntity):
        entity_upload = EntityUploadStatus.objects.filter(
            revised_geographical_entity=obj
        ).first()
        if entity_upload:
            return entity_upload.upload_session.uploader.username
        if obj.approved_by:
            return obj.approved_by.username
        if obj.dataset.created_by:
            return obj.dataset.created_by.username
        return ''

    def get_reviewable(self, obj: GeographicalEntity):
        return not obj.is_approved and self.context['user'].is_superuser

    def get_revision(self, obj: GeographicalEntity):
        return obj.revision_number

    class Meta:
        model = GeographicalEntity
        fields = [
            'id',
            'revision',
            'date',
            'is_approved',
            'reviewable',
            'uploader',
            'status'
        ]


class EntityRevisionList(APIView):
    """
    List revisions for an entity
    """
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        entity = get_object_or_404(
            GeographicalEntity,
            id=request.GET.get('id', '')
        )
        entities = GeographicalEntity.objects.filter(
            uuid=entity.uuid
        ).order_by('-revision_number')
        return Response(
            EntityRevisionSerializer(
                entities, many=True, context={
                    'user': self.request.user
                }
            ).data
        )


class EntityByConceptUCode(APIView):
    """
    Find Entity detail by Concept UCode
    """
    permission_classes = [IsAuthenticated]

    def check_external_user_in_views(self, user, dataset):
        # try to look for external user of views in dataset
        privacy_level = 0
        dataset_views = DatasetView.objects.filter(
            dataset=dataset
        )
        dataset_views = get_objects_for_user(
            user,
            EXTERNAL_READ_VIEW_PERMISSION_LIST,
            klass=dataset_views,
            use_groups=True,
            any_perm=True,
            accept_global_perms=False
        )
        for view in dataset_views:
            view_privacy_level = get_external_view_permission_privacy_level(
                user,
                view
            )
            privacy_level = max(privacy_level, view_privacy_level)
            if privacy_level == 4:
                break
        return privacy_level

    def get(self, request, *args, **kwargs):
        concept_ucode = kwargs.get('concept_ucode')
        entities = GeographicalEntity.objects.filter(
            is_approved=True,
            concept_ucode=concept_ucode
        )
        entity = entities.first()
        if not entity:
            raise Http404(
                "No entity matches the given Concept Ucode."
            )
        dataset = entity.dataset
        privacy_level = get_view_permission_privacy_level(
            request.user,
            dataset
        )
        if privacy_level <= 0:
            privacy_level = self.check_external_user_in_views(
                request.user,
                dataset
            )
            if privacy_level <= 0:
                return HttpResponseForbidden('No permission')
        entities = entities.filter(
            privacy_level__lte=privacy_level
        )
        return Response(
            EntityConceptUCodeSerializer(
                dataset, many=False, context={
                    'concept_ucode': concept_ucode,
                    'user': request.user,
                    'entities': entities
                }
            ).data
        )


class EntityEdit(APIView):
    """
    Edit Entitiy
    """
    permission_classes = [IsAuthenticated]

    def _check_can_edit(self, user, dataset):
        checker = ObjectPermissionChecker(user)
        can_edit = checker.has_perm('edit_metadata_dataset', dataset)
        return can_edit

    def post(self, request, entity_id: int, *args, **kwargs):
        entity = get_object_or_404(GeographicalEntity, id=entity_id)
        can_edit = self._check_can_edit(request.user, entity.dataset)
        if not can_edit:
            return Response({
                'detail': 'Insufficient permission'
            }, 403)
        serializer = EntityEditSerializer(
            data=request.data,
            context={
                'codes': request.data.get('codes', []),
                'names': request.data.get('names', []),
                'type': request.data.get('type', None)
            }
        )
        serializer.is_valid(raise_exception=True)
        if request.data.get('is_dirty', False):
            entity = serializer.save()
            check_affected_dataset_views.delay(entity.dataset.id, entity.id)
            entity.refresh_from_db()
        return Response(EntityEditSerializer(entity).data, 200)

    def get(self, request, entity_id: int, *args, **kwargs):
        entity = get_object_or_404(GeographicalEntity, id=entity_id)
        can_edit = self._check_can_edit(request.user, entity.dataset)
        if not can_edit:
            return Response({
                'detail': 'Insufficient permission'
            }, 403)
        return Response(EntityEditSerializer(entity).data, 200)


class BatchEntityEditAPI(APIView):
    """API to fetch and create/update batch entity edit for given dataset."""
    permission_classes = [IsAuthenticated]

    def find_existing_batch(self, dataset: Dataset):
        batch_edit = BatchEntityEdit.objects.filter(
            dataset=dataset
        ).exclude(
            status__in=COMPLETED_STATUS
        ).order_by('-id')
        return batch_edit.first()

    def put(self, *args, **kwargs):
        dataset_id = self.request.GET.get('dataset_id')
        dataset = get_object_or_404(Dataset, id=dataset_id)
        existing_batch_edit = self.find_existing_batch(dataset)
        if existing_batch_edit:
            return Response({
                'detail': (
                    'There is ongoing batch entity edit for this dataset!'
                ),
                'batch_id': existing_batch_edit.id
            }, 400)
        batch_edit = BatchEntityEdit.objects.create(
            dataset=dataset,
            status=PENDING,
            submitted_by=self.request.user,
            submitted_on=timezone.now()
        )
        return Response(
            status=200, data=BatchEntityEditSerializer(batch_edit).data)

    def get(self, *args, **kwargs):
        dataset_id = self.request.GET.get('dataset_id')
        dataset = get_object_or_404(Dataset, id=dataset_id)
        batch_edit_id = self.request.GET.get('batch_edit_id', None)
        if batch_edit_id:
            batch_edit = get_object_or_404(BatchEntityEdit, id=batch_edit_id)
        else:
            batch_edit = self.find_existing_batch(dataset)
            if batch_edit is None:
                return Response(status=404, data={
                    'detail': (
                        'There is no ongoing batch entity edit '
                        'for this dataset!'
                    )
                })
        return Response(
            status=200, data=BatchEntityEditSerializer(batch_edit).data)

    def post(self, *args, **kwargs):
        """Update fields mappping and trigger the importer."""
        batch_edit_id = self.request.data.get('batch_edit_id')
        batch_edit = get_object_or_404(BatchEntityEdit, id=batch_edit_id)
        ucode_field = self.request.data.get('ucode_field')
        id_fields = self.request.data.get('id_fields')
        name_fields = self.request.data.get('name_fields')
        batch_edit.ucode_field = ucode_field
        if id_fields:
            batch_edit.id_fields = id_fields
        if name_fields:
            batch_edit.name_fields = name_fields
        if batch_edit.task_id:
            cancel_task(batch_edit.task_id)
        task = process_batch_entity_edit.delay(batch_edit.id, False)
        batch_edit.task_id = task.id
        batch_edit.save(
            update_fields=[
                'id_fields', 'name_fields', 'ucode_field',
                'task_id'
            ]
        )
        return Response(
            status=200, data=BatchEntityEditSerializer(batch_edit).data)


class BatchEntityEditFile(APIView):
    """API to upload/download batch entity edit."""

    def validate(self, batch_edit: BatchEntityEdit):
        """
        Validation of file input:
        - File type: excel or csv
        - Column Headers > 0
        - Total rows > 0
        """
        importer = get_entity_edit_importer(batch_edit, True)
        if importer is None:
            # invalid file type
            return False, (
                'Invalid file type! Please upload either excel or csv file!'
            )
        return importer.validate_input_file()

    def post(self, request, format=None):
        file_obj = request.FILES['file']
        batch_edit_id = request.data.get('batch_edit_id')
        batch_edit = get_object_or_404(BatchEntityEdit, id=batch_edit_id)
        batch_edit.input_file = file_obj
        batch_edit.save(update_fields=['input_file'])
        valid_file, error = self.validate(batch_edit)
        if not valid_file:
            return Response(
                status=400,
                data={
                    'detail': error
                }
            )
        return Response(status=204)

    def delete(self, request, format=None):
        batch_edit_id = request.GET.get('batch_edit_id')
        batch_edit = get_object_or_404(BatchEntityEdit, id=batch_edit_id)
        if batch_edit.input_file:
            try_delete_uploaded_file(batch_edit.input_file)
        batch_edit.input_file = None
        if batch_edit.output_file:
            try_delete_uploaded_file(batch_edit.output_file)
            batch_edit.output_file = None
        batch_edit.finished_at = None
        batch_edit.progress = 0
        batch_edit.errors = None
        batch_edit.error_notes = None
        batch_edit.error_count = 0
        batch_edit.success_notes = None
        batch_edit.total_count = 0
        batch_edit.success_count = 0
        batch_edit.status = PENDING
        batch_edit.headers = []
        batch_edit.save(update_fields=[
            'status', 'started_at', 'progress', 'errors',
            'finished_at', 'output_file', 'error_notes',
            'error_count', 'total_count', 'success_notes',
            'success_count', 'input_file', 'headers'
        ])
        return Response(status=204)


class BatchEntityEditResultAPI(APIView):
    """API to fetch the result from batch entity edit."""
    permission_classes = [IsAuthenticated]

    def get(self, *args, **kwargs):
        batch_edit_id = self.request.GET.get('batch_edit_id')
        batch_edit = get_object_or_404(BatchEntityEdit, id=batch_edit_id)
        if batch_edit.status != DONE or batch_edit.output_file is None:
            return Response(
                status=400,
                data={
                    'detail': (
                        'Unable to fetch the output from batch edit '
                        f'with status {batch_edit.status}'
                    )
                }
            )
        with batch_edit.output_file.open('rb') as csv_file:
            file = csv_file.read().decode(
                'utf-8', errors='ignore').splitlines()
            csv_reader = csv.DictReader(file)
            data = [row for row in csv_reader]
        return Response(status=200, data=data)
