from django.db import models
from django.utils.text import slugify


class LayerStyle(models.Model):
    FILL = 'fill'
    LINE = 'line'
    SYMBOL = 'symbol'
    CIRCLE = 'circle'
    STYLE_TYPE_CHOICES = [
        (FILL, 'Fill'),
        (LINE, 'Line'),
        (SYMBOL, 'Symbol'),
        (CIRCLE, 'Circle'),
    ]

    label = models.CharField(
        max_length=128,
        null=False,
        blank=False
    )

    dataset = models.ForeignKey(
        'georepo.Dataset',
        null=False,
        blank=False,
        on_delete=models.CASCADE
    )

    level = models.IntegerField(
        null=False,
        blank=False,
        default=0
    )

    style = models.JSONField(
        null=True,
        blank=True
    )

    type = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        choices=STYLE_TYPE_CHOICES
    )

    max_zoom = models.IntegerField(
        default=8
    )

    min_zoom = models.IntegerField(
        default=1
    )

    def __str__(self):
        return self.label

    def save(self, *args):
        if self.style:
            if 'maxzoom' in self.style:
                self.max_zoom = self.style['maxzoom']
            if 'minzoom' in self.style:
                self.min_zoom = self.style['minzoom']
            if 'type' in self.style:
                self.type = self.style['type']
        super(LayerStyle, self).save(*args)

    @property
    def vector_layer_obj(self):
        """
        Returns vector layer object and style included
        """
        layer = self.style if self.style else {}
        layer['maxzoom'] = self.max_zoom
        layer['minzoom'] = self.min_zoom
        layer['type'] = self.type
        layer['source'] = self.dataset.label
        layer['id'] = slugify(self.label)
        layer['source-layer'] = f'Level-{self.level}'
        return layer
