from datetime import datetime
from django.core.mail import send_mail
from django.urls import reverse
from django.template.loader import render_to_string
from django import forms
from django.http import HttpResponseRedirect
from django.views.generic.edit import FormView
from captcha.fields import CaptchaField
from django.conf import settings
from core.models.preferences import SitePreferences
from georepo.models.access_request import UserAccessRequest


class SignUpForm(forms.Form):
    required_css_class = 'required'
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField(max_length=255, required=True)
    description = forms.CharField(max_length=512, required=True,
                                  widget=forms.Textarea(attrs={'cols': 30}))
    captcha = CaptchaField()

    def send_email(self, request_obj: UserAccessRequest, request):
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
            request.build_absolute_uri(
                reverse('dashboard-view')
            ) + f'access_request?id={request_obj.id}'
        )
        if not settings.DEBUG:
            # if not dev env, then replace with https
            url = url.replace('http://', 'https://')
        context = {
            'request_name': 'New Sign Up',
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

    def save(self, request):
        access_request = UserAccessRequest.objects.create(
            type=UserAccessRequest.RequestType.NEW_USER,
            status=UserAccessRequest.RequestStatus.PENDING,
            submitted_on=datetime.now(),
            requester_first_name=self.cleaned_data['first_name'],
            requester_last_name=self.cleaned_data['last_name'],
            requester_email=self.cleaned_data['email'],
            description=self.cleaned_data['description']
        )
        self.send_email(access_request, request)


class SignUpView(FormView):
    template_name = 'user_signup.html'
    form_class = SignUpForm
    success_url = "/sign-up/?success=true"

    def form_valid(self, form):
        if form.is_valid():
            # if user has pending request, then skip save
            check_exist = UserAccessRequest.objects.filter(
                type=UserAccessRequest.RequestType.NEW_USER,
                status=UserAccessRequest.RequestStatus.PENDING,
                requester_email=form.cleaned_data['email']
            ).exists()
            if not check_exist:
                form.save(self.request)
        return super().form_valid(form)

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return HttpResponseRedirect('dashboard-view')
        return super(SignUpView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sign_up_success'] = self.request.GET.get('success', False)
        return context
