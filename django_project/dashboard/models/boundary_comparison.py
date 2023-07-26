from django.contrib.gis.db import models


class BoundaryComparison(models.Model):

    main_boundary = models.ForeignKey(
        'georepo.GeographicalEntity',
        related_name='main_boundary',
        null=False,
        blank=False,
        on_delete=models.CASCADE
    )

    comparison_boundary = models.ForeignKey(
        'georepo.GeographicalEntity',
        related_name='comparison_boundary',
        blank=True,
        null=True,
        on_delete=models.CASCADE
    )

    code_match = models.BooleanField(
        null=True,
        blank=True,
        default=None
    )

    name_similarity = models.FloatField(
        null=True,
        blank=True
    )

    geometry_overlap_new = models.FloatField(
        null=True,
        blank=True,
        help_text='Overlap new area covered by old area'
    )

    geometry_overlap_old = models.FloatField(
        null=True,
        blank=True,
        help_text='Overlap old area covered by new area'
    )

    centroid_distance = models.FloatField(
        null=True,
        blank=True
    )

    is_parent_rematched = models.BooleanField(
        default=False,
        help_text='True if rematched parent has different default code'
    )

    is_same_entity = models.BooleanField(
        null=True,
        blank=True,
        help_text=(
            'Same entity concept, '
            'True if both similarities are above thresholds. '
            'This can be manually changed by end user'
        )
    )
