from datetime import datetime
from django.core.mail import send_mail
from django.urls import reverse
from django.template.loader import render_to_string
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.conf import settings
from core.models.preferences import SitePreferences
from georepo.models.access_request import UserAccessRequest
from dashboard.api_views.common import IsSuperUser
from dashboard.serializers.access_request import (
    AccessRequestSerializer,
    AccessRequestDetailSerializer
)


ACCESS_REQUEST_TYPE_LIST = {
    'user': UserAccessRequest.RequestType.NEW_USER,
    'permission': UserAccessRequest.RequestType.NEW_PERMISSIONS
}
User = get_user_model()


class AccessRequestList(APIView):
    """List access request."""
    permission_classes = [IsSuperUser]

    def get(self, request, *args, **kwargs):
        request_type = kwargs.get('type')
        if request_type not in ACCESS_REQUEST_TYPE_LIST:
            raise ValidationError(f'Invalid reqyest type: {request_type}')
        status = request.GET.get('status', None)
        results = UserAccessRequest.objects.filter(
            type=ACCESS_REQUEST_TYPE_LIST[request_type]
        ).order_by('-submitted_on')
        if status:
            results = results.filter(status=status)
        return Response(status=200, data=AccessRequestSerializer(
            results, many=True
        ).data)


class AccessRequestDetail(APIView):
    """Approve/Reject access request."""
    permission_classes = [IsSuperUser]

    def approval_request(self, request_obj: UserAccessRequest,
                         is_approve: bool, remarks: str):
        request_obj.approved_date = datetime.now()
        request_obj.approved_by = self.request.user
        request_obj.approver_notes = remarks
        request_obj.status = (
            UserAccessRequest.RequestStatus.APPROVED if is_approve else
            UserAccessRequest.RequestStatus.REJECTED
        )
        request_obj.save()

    def notify_requester_new_user(self, request_obj: UserAccessRequest):
        request_from = '-'
        if request_obj.requester_first_name:
            request_from = request_obj.requester_first_name
            if request_obj.requester_last_name:
                request_from = (
                    f'{request_from} {request_obj.requester_last_name}'
                )
        request_from = (
            request_obj.requester_email if request_from == '-' else
            request_from
        )
        url = self.request.build_absolute_uri(reverse('dashboard-view'))
        if not settings.DEBUG:
            # if not dev env, then replace with https
            url = url.replace('http://', 'https://')
        context = {
            'is_approved': (
                request_obj.status == UserAccessRequest.RequestStatus.APPROVED
            ),
            'request_from': request_from,
            'has_admin_remarks': (
                request_obj.approver_notes and
                len(request_obj.approver_notes) > 0
            ),
            'admin_remarks': request_obj.approver_notes,
            'url': url
        }
        subject = ''
        if request_obj.status == UserAccessRequest.RequestStatus.APPROVED:
            subject = 'Success! Your GeoRepo account has been created'
        else:
            subject = 'Your GeoRepo account request has been rejected'
        message = render_to_string(
            'emails/notify_signup_request.html',
            context
        )
        send_mail(
            subject,
            None,
            settings.DEFAULT_FROM_EMAIL,
            [request_obj.requester_email],
            html_message=message,
            fail_silently=False
        )

    def notify_requester_access_request(self, request_obj: UserAccessRequest):
        request_from = '-'
        if request_obj.requester_first_name:
            request_from = request_obj.requester_first_name
            if request_obj.requester_last_name:
                request_from = (
                    f'{request_from} {request_obj.requester_last_name}'
                )
        request_from = (
            request_obj.requester_email if request_from == '-' else
            request_from
        )
        url = self.request.build_absolute_uri(
            reverse('dashboard-view')
        )
        if not settings.DEBUG:
            # if not dev env, then replace with https
            url = url.replace('http://', 'https://')
        context = {
            'is_approved': (
                request_obj.status == UserAccessRequest.RequestStatus.APPROVED
            ),
            'request_from': request_from,
            'has_admin_remarks': (
                request_obj.approver_notes and
                len(request_obj.approver_notes) > 0
            ),
            'admin_remarks': request_obj.approver_notes,
            'url': url
        }
        subject = ''
        if request_obj.status == UserAccessRequest.RequestStatus.APPROVED:
            subject = 'Success! Your access request has been approved'
        else:
            subject = 'Your access request has been rejected'
        message = render_to_string(
            'emails/notify_access_request.html',
            context
        )
        send_mail(
            subject,
            None,
            settings.DEFAULT_FROM_EMAIL,
            [request_obj.requester_email],
            html_message=message,
            fail_silently=False
        )

    def approve_new_user_access(self, request_obj: UserAccessRequest):
        # create new user + set as viewer
        new_user = User.objects.create(
            first_name=request_obj.requester_first_name,
            last_name=(
                request_obj.requester_last_name if
                request_obj.requester_last_name else ''
            ),
            username=request_obj.requester_email,
            email=request_obj.requester_email,
            is_active=True
        )
        request_obj.request_by = new_user
        request_obj.save()
        return new_user

    def get(self, request, *args, **kwargs):
        request_id = kwargs.get('request_id')
        request_obj = get_object_or_404(UserAccessRequest, id=request_id)
        return Response(
            status=200,
            data=AccessRequestDetailSerializer(request_obj).data
        )

    def post(self, request, *args, **kwargs):
        request_id = kwargs.get('request_id')
        request_obj = get_object_or_404(UserAccessRequest, id=request_id)
        is_approve = request.data.get('is_approve')
        remarks = request.data.get('remarks', None)
        # validate if status is Pending
        if request_obj.status != UserAccessRequest.RequestStatus.PENDING:
            return Response(status=400, data={
                'detail': 'The request has been processed!'
            })
        # store approval
        self.approval_request(request_obj, is_approve, remarks)
        requester = None
        if request_obj.type == UserAccessRequest.RequestType.NEW_USER:
            if is_approve:
                requester = self.approve_new_user_access(request_obj)
        else:
            requester = request_obj.request_by
        # notify requester
        if request_obj.type == UserAccessRequest.RequestType.NEW_USER:
            self.notify_requester_new_user(request_obj)
        else:
            self.notify_requester_access_request(request_obj)
        return Response(status=201, data={
            'requester_id': requester.id if requester else None
        })


class SubmitPermissionAccessRequest(APIView):
    """Manage permission access request."""
    permission_classes = [IsAuthenticated]

    def check_has_pending_request(self):
        return UserAccessRequest.objects.filter(
            request_by=self.request.user,
            status=UserAccessRequest.RequestStatus.PENDING,
            type=UserAccessRequest.RequestType.NEW_PERMISSIONS
        ).order_by('id').first()

    def notify_admin(self, request_obj: UserAccessRequest):
        admin_emails = SitePreferences.preferences().default_admin_emails
        if not admin_emails:
            return
        name_of_user = '-'
        if request_obj.requester_first_name:
            name_of_user = request_obj.requester_first_name
            if request_obj.requester_last_name:
                name_of_user = (
                    f'{name_of_user} {request_obj.requester_last_name}'
                )
        request_from = (
            request_obj.requester_email if name_of_user == '-' else
            name_of_user
        )
        url = (
            self.request.build_absolute_uri(
                reverse('dashboard-view')
            ) + f'access_request?id={request_obj.id}'
        )
        if not settings.DEBUG:
            # if not dev env, then replace with https
            url = url.replace('http://', 'https://')
        context = {
            'request_name': 'New Access',
            'request_from': request_from,
            'name_of_user': name_of_user,
            'email_of_user': request_obj.requester_email,
            'description': request_obj.description,
            'url': url
        }
        subject = f'New Access Request from {request_from}'
        message = render_to_string(
            'emails/notify_new_request.html',
            context
        )
        send_mail(
            subject,
            None,
            settings.DEFAULT_FROM_EMAIL,
            admin_emails,
            html_message=message,
            fail_silently=False
        )

    def get(self, request, *args, **kwargs):
        # Check whether user has pending request
        pending_request = self.check_has_pending_request()
        previous_requests = UserAccessRequest.objects.filter(
            request_by=self.request.user,
            status__in=[
                UserAccessRequest.RequestStatus.APPROVED,
                UserAccessRequest.RequestStatus.REJECTED
            ],
            type=UserAccessRequest.RequestType.NEW_PERMISSIONS
        ).order_by('-id')
        return Response(status=200, data={
            'has_pending_request': pending_request is not None,
            'request': (
                AccessRequestDetailSerializer(pending_request).data if
                pending_request else None
            ),
            'previous_requests': (
                AccessRequestDetailSerializer(
                    previous_requests,
                    many=True
                ).data
            ),
            'user_email': request.user.email
        })

    def post(self, request, *args, **kwargs):
        # Submit new permission access request
        if self.check_has_pending_request():
            return Response(status=400, data={
                'detail': 'You have pending request!'
            })
        user = self.request.user
        # validate user has email
        user_email = user.email if user.email else request.data.get(
            'user_email'
        )
        if not user_email:
            return Response(status=400, data={
                'detail': 'Please provide a valid email address!'
            })
        if not user.email and user_email:
            user.email = user_email
            user.save(update_fields=['email'])
        request_obj = UserAccessRequest.objects.create(
            type=UserAccessRequest.RequestType.NEW_PERMISSIONS,
            status=UserAccessRequest.RequestStatus.PENDING,
            submitted_on=datetime.now(),
            requester_first_name=user.first_name,
            requester_last_name=user.last_name,
            requester_email=user.email,
            description=request.data.get('description'),
            request_by=user
        )
        self.notify_admin(request_obj)
        return Response(status=201, data={
            'id': request_obj.id
        })
