# coding=utf-8
"""Health check API urls."""

from django.urls import path
from . import views

urlpatterns = [
    path('ready/', views.readiness_probe, name='health-readiness'),
]
