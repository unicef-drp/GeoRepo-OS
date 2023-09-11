from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from guardian.core import ObjectPermissionChecker
from rest_framework import serializers
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from guardian.shortcuts import get_objects_for_user
from dashboard.models import EntityUploadStatus
from georepo.models import (
    GeographicalEntity,
    DatasetView,
)
from georepo.utils.permission import (
    EXTERNAL_READ_VIEW_PERMISSION_LIST,
    get_view_permission_privacy_level,
    get_external_view_permission_privacy_level
)
from dashboard.serializers.entity import (
    EntityConceptUCodeSerializer,
    EntityEditSerializer
)


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
        serializer.save()
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
