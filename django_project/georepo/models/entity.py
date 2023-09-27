from uuid import uuid4

from django.conf import settings
from django.contrib.gis.db import models
from django.db import IntegrityError, transaction

# revision uuid
UUID_ENTITY_ID = 'uuid'
# concept uuid
CONCEPT_UUID_ENTITY_ID = 'concept_uuid'
# concept ucode
CONCEPT_UCODE_ENTITY_ID = 'concept_ucode'
# default code
CODE_ENTITY_ID = 'code'
# ucode
UCODE_ENTITY_ID = 'ucode'
MAIN_ENTITY_ID_LIST = [
    UUID_ENTITY_ID, CODE_ENTITY_ID,
    CONCEPT_UUID_ENTITY_ID, UCODE_ENTITY_ID,
    CONCEPT_UCODE_ENTITY_ID
]


class GeographicalEntity(models.Model):
    id = models.AutoField(primary_key=True)

    dataset = models.ForeignKey(
        'georepo.Dataset',
        null=True,
        blank=True,
        on_delete=models.CASCADE
    )

    uuid = models.UUIDField(
        default=uuid4,
        help_text='concept UUID'
    )

    uuid_revision = models.UUIDField(
        blank=True,
        default=uuid4,
        help_text='uuid for each revision'
    )

    revision_number = models.IntegerField(
        null=True,
        blank=True
    )

    unique_code = models.CharField(
        default='',
        max_length=128,
        blank=True,
    )

    unique_code_version = models.FloatField(
        null=True,
        blank=True
    )

    concept_ucode = models.CharField(
        default='',
        max_length=255,
        blank=True,
        help_text='Concept UCode'
    )

    internal_code = models.CharField(
        null=True,
        blank=True,
        max_length=255
    )

    level = models.IntegerField(
        default=0
    )

    label = models.CharField(
        null=True,
        blank=True,
        max_length=255
    )

    start_date = models.DateTimeField(
        null=True,
        blank=True
    )

    end_date = models.DateTimeField(
        null=True,
        blank=True
    )

    is_latest = models.BooleanField(
        null=True,
        blank=True,
    )

    is_approved = models.BooleanField(
        null=True,
        blank=True
    )

    is_private = models.BooleanField(
        default=False
    )

    is_validated = models.BooleanField(
        default=False
    )

    approved_date = models.DateTimeField(
        null=True,
        blank=True
    )

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    geometry = models.GeometryField(
        null=True
    )

    source = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    source_url = models.URLField(
        null=True,
        blank=True
    )

    license = models.TextField(
        null=True,
        blank=True
    )

    qc_notes = models.TextField(
        verbose_name='QC Notes',
        null=True,
        blank=True
    )

    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children'
    )

    type = models.ForeignKey(
        'georepo.EntityType',
        on_delete=models.CASCADE,
        null=False,
        blank=False
    )

    layer_file = models.ForeignKey(
        'dashboard.LayerFile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    version = models.IntegerField(
        null=True,
        blank=True
    )

    feature_units = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    area = models.FloatField(
        null=True,
        blank=True
    )

    perimeter = models.FloatField(
        help_text='The total length of borders',
        null=True,
        blank=True,
    )

    vertices = models.PositiveIntegerField(
        help_text='The total number of line vertices',
        null=True,
        blank=True
    )

    vertex_density = models.FloatField(
        help_text=(
            'The average number of vertices for every km of line distance. '
            'Calculated as the total number of vertices of all boundary units '
            'divided by the total perimeter.'
        ),
        null=True,
        blank=True
    )

    line_resolution = models.FloatField(
        help_text=(
            "The average resolution or distance between line vertices. "
            "Calculated as the total perimeter of all boundary units "
            "divided by the total number of vertices."
        ),
        null=True,
        blank=True
    )

    ancestor = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text='Parent Level 0'
    )

    admin_level_name = models.CharField(
        null=True,
        blank=True,
        max_length=255
    )

    privacy_level = models.IntegerField(
        default=4
    )

    @property
    def ucode(self):
        from georepo.utils import get_unique_code
        return get_unique_code(self.unique_code, self.unique_code_version)

    class Meta:
        verbose_name_plural = 'Geographical Entities'
        ordering = ['start_date']
        indexes = [
                    models.Index(fields=['internal_code']),
                    models.Index(fields=['label']),
                    models.Index(fields=['level']),
                    models.Index(fields=['revision_number']),
                    models.Index(fields=['concept_ucode']),
                    models.Index(fields=['unique_code'])
                ]

    def __str__(self):
        return (
            f'{self.label} : '
            f'Revision {self.revision_number} : '
            f'Level {self.level} : '
            f'{self.dataset.label}'
        )

    def all_children(self):
        from django.db.models import Q
        max_level: int = 0
        max_level_entity = GeographicalEntity.objects.all().order_by(
            'level').last()
        if max_level_entity:
            max_level = max_level_entity.level
        parent_id_key = 'id'
        ancestor_filters = Q(**{parent_id_key: self.id})
        for i in range(max_level):
            parent_id_key = 'parent__' + parent_id_key
            ancestor_filters |= Q(**{parent_id_key: self.id})
        return GeographicalEntity.objects.filter(
            ancestor_filters,
        )


class EntityName(models.Model):
    id = models.AutoField(primary_key=True)

    name = models.CharField(
        blank=False,
        null=False,
        max_length=255
    )

    geographical_entity = models.ForeignKey(
        'georepo.GeographicalEntity',
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        related_name="entity_names"
    )

    language = models.ForeignKey(
        'georepo.Language',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    default = models.BooleanField(
        default=False
    )

    label = models.CharField(
        help_text='Examples: Alt Name.',
        blank=True,
        null=True,
        default='',
        max_length=255
    )

    idx = models.IntegerField(
        null=True,
        blank=True
    )

    class Meta:
        indexes = [models.Index(fields=['name'])]


class EntityTypeManager(models.Manager):
    def get_by_label(self, label: str):
        """Get or create with unique_constraint check."""
        entity_type = self.filter(
            label=label
        ).first()
        if entity_type is None:
            try:
                with transaction.atomic():
                    entity_type = self.create(
                        label=label
                    )
            except IntegrityError:
                entity_type = self.get(
                    label=label
                )
        return entity_type


class EntityType(models.Model):
    objects = EntityTypeManager()
    id = models.AutoField(primary_key=True)

    label = models.CharField(
        help_text='Examples: Country, Region, etc.',
        blank=False,
        null=False,
        max_length=255
    )

    label_plural = models.CharField(
        help_text='Examples: Countries, Regions, etc.',
        blank=True,
        null=True,
        max_length=255
    )

    def __str__(self):
        return self.label

    class Meta:
        constraints = [
            models.UniqueConstraint(
                name='unique_entity_type_label',
                fields=['label']
            )
        ]


class EntityId(models.Model):
    geographical_entity = models.ForeignKey(
        'georepo.GeographicalEntity',
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        related_name="entity_ids"
    )

    code = models.ForeignKey(
        'georepo.IdType',
        on_delete=models.CASCADE,
        null=False,
        blank=False
    )

    value = models.CharField(
        null=False,
        blank=False,
        max_length=255
    )

    default = models.BooleanField(
        default=False
    )

    class Meta:
        indexes = [models.Index(fields=['value'])]


class EntitySimplified(models.Model):
    geographical_entity = models.ForeignKey(
        'georepo.GeographicalEntity',
        on_delete=models.CASCADE,
        null=False,
        blank=False
    )

    simplify_tolerance = models.FloatField(
        default=0
    )

    simplified_geometry = models.GeometryField(
        null=True
    )

    dataset_view = models.ForeignKey(
        'georepo.DatasetView',
        null=True,
        blank=True,
        on_delete=models.CASCADE
    )


# @receiver(post_save, sender=EntityName)
# def entity_name_post_create(
#     sender, instance: EntityName, created, *args, **kwargs
# ):
#     if getattr(instance, 'skip_signal', False):
#         return
#     if created and instance.geographical_entity.is_approved:
#         instance.geographical_entity.dataset.set_view_out_of_sync(
#             vector_tile=True,
#             product=True
#         )
#
#
# @receiver(post_delete, sender=EntityName)
# def entity_name_post_delete(
#     sender, instance: EntityName, *args, **kwargs
# ):
#     if getattr(instance, 'skip_signal', False):
#         return
#     try:
#         instance.geographical_entity.dataset.set_view_out_of_sync(
#             vector_tile=True,
#             product=True
#         )
#     except GeographicalEntity.DoesNotExist:
#         pass
#
#
# @receiver(pre_save, sender=EntityName)
# def entity_name_edit(
#     sender, instance: EntityName, *args, **kwargs
# ):
#     if getattr(instance, 'skip_signal', False):
#         return
#     if instance.id and instance.geographical_entity.is_approved:
#         old_instance: EntityName = EntityName.objects.get(id=instance.id)
#         if (
#             old_instance.name != instance.name or
#             old_instance.language != instance.language or
#             old_instance.default != instance.default
#         ):
#             instance.geographical_entity.dataset.set_view_out_of_sync(
#                 vector_tile=True,
#                 product=True
#             )
#
#
# @receiver(post_save, sender=EntityId)
# def entity_id_post_create(
#     sender, instance: EntityId, created, *args, **kwargs
# ):
#     if getattr(instance, 'skip_signal', False):
#         return
#     if created and instance.geographical_entity.is_approved:
#         instance.geographical_entity.dataset.set_view_out_of_sync(
#             vector_tile=True,
#             product=True
#         )
#
#
# @receiver(post_delete, sender=EntityId)
# def entity_id_post_delete(
#     sender, instance: EntityId, *args, **kwargs
# ):
#     if getattr(instance, 'skip_signal', False):
#         return
#     try:
#         instance.geographical_entity.dataset.set_view_out_of_sync(
#             vector_tile=True,
#             product=True
#         )
#     except GeographicalEntity.DoesNotExist:
#         pass
#
#
# @receiver(pre_save, sender=EntityId)
# def entity_id_edit(
#     sender, instance: EntityId, *args, **kwargs
# ):
#     if getattr(instance, 'skip_signal', False):
#         return
#     if instance.id and instance.geographical_entity.is_approved:
#         old_instance: EntityId = EntityId.objects.get(id=instance.id)
#         if (
#             old_instance.value != instance.value or
#             old_instance.code != instance.code or
#             old_instance.default != instance.default
#         ):
#             instance.geographical_entity.dataset.set_view_out_of_sync(
#                 vector_tile=True,
#                 product=True
#             )
