from django.db import models
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _


class GeorepoRole(models.Model):

    class RoleType(models.TextChoices):
        CREATOR = 'Creator', _('Creator')
        VIEWER = 'Viewer', _('Viewer')

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    type = models.CharField(
        null=True,
        blank=True,
        max_length=255,
        choices=RoleType.choices,
        default=RoleType.VIEWER
    )


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_role(sender, instance, created, **kwargs):
    if created:
        GeorepoRole.objects.get_or_create(
            user=instance,
            type=GeorepoRole.RoleType.VIEWER
        )


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def save_user_role(sender, instance, **kwargs):
    instance.georeporole.save()
