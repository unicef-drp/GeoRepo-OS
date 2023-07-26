from django.db import models
from django.utils.translation import gettext_lazy as _

from taggit.models import TagBase, GenericTaggedItemBase


class TagWithDescription(TagBase):
    description = models.TextField(null=True, blank=True)

    class Meta:
        verbose_name = _("Tag")
        verbose_name_plural = _("Tags")


class TaggedRecord(GenericTaggedItemBase):
    tag = models.ForeignKey(
        TagWithDescription,
        on_delete=models.CASCADE,
        related_name="%(app_label)s_%(class)s_items",
    )
