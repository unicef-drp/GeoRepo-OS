import uuid
from django.db import models
from django.conf import settings
from guardian.models import UserObjectPermissionBase
from guardian.models import GroupObjectPermissionBase


class Module(models.Model):
    class Meta:
        permissions = [
            ('toggle_status_module', 'Enable/Disable Module'),
            ('module_add_dataset', 'Create New Dataset')
        ]

    name = models.CharField(
        max_length=255,
        null=False,
        blank=False
    )

    description = models.TextField(
        max_length=255,
        default='',
        blank=True
    )

    dataset_entity_name = models.CharField(
        max_length=255,
        null=False,
        blank=False
    )

    dataset_entity_name_plural = models.CharField(
        max_length=255,
        null=False,
        blank=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    default_module = models.BooleanField(
        default=False
    )

    uuid = models.UUIDField(
        default=uuid.uuid4,
        blank=True
    )

    is_active = models.BooleanField(
        default=True,
        help_text='To enable/disable module',
    )

    deactivated_at = models.DateTimeField(
        null=True,
        blank=True
    )

    deactivated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='deactivated_module'
    )

    @property
    def code_name(self):
        return self.name.lower().replace(' ', '_')

    def save(self, *args, **kwargs):
        if self.default_module:
            Module.objects.exclude(id=self.id).update(default_module=False)
        return super(Module, self).save(*args, **kwargs)

    def __str__(self):
        return self.name


class ModuleUserObjectPermission(UserObjectPermissionBase):
    content_object = models.ForeignKey(Module, on_delete=models.CASCADE)


class ModuleGroupObjectPermission(GroupObjectPermissionBase):
    content_object = models.ForeignKey(Module, on_delete=models.CASCADE)
