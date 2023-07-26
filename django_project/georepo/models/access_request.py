from uuid import uuid4
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class UserAccessRequest(models.Model):
    """Model to store any request from user."""

    class RequestType(models.TextChoices):
        NEW_USER = 'NEW_USER', _('NEW_USER')
        NEW_PERMISSIONS = 'NEW_PERMISSIONS', _('NEW_PERMISSIONS')

    class RequestStatus(models.TextChoices):
        PENDING = 'PENDING', _('PENDING')
        APPROVED = 'APPROVED', _('APPROVED')
        REJECTED = 'REJECTED', _('REJECTED')

    type = models.CharField(
        max_length=255,
        choices=RequestType.choices
    )

    status = models.CharField(
        max_length=255,
        choices=RequestStatus.choices,
        default=RequestStatus.PENDING
    )

    uuid = models.UUIDField(
        default=uuid4
    )

    submitted_on = models.DateTimeField()

    requester_first_name = models.CharField(
        null=True,
        blank=True,
        max_length=150
    )

    requester_last_name = models.CharField(
        null=True,
        blank=True,
        max_length=150
    )

    requester_email = models.EmailField(max_length=255)

    description = models.CharField(
        max_length=512,
        null=False,
        blank=False
    )

    request_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='accessrequests_submitted'
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
        related_name='accessrequests_approval'
    )

    approver_notes = models.CharField(
        max_length=512,
        null=True,
        blank=True
    )

    action_results = models.JSONField(
        null=True,
        blank=True,
        help_text='Approval results, e.g. added permissions'
    )
