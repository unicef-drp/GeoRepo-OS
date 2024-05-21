# -*- coding: utf-8 -*-
"""Utilities for project."""
import os

# Absolute filesystem path to the Django project directory:
DJANGO_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    ))


def absolute_path(*args):
    """Return absolute path of django project."""
    # check if it's running inside vscode container
    path = os.path.join(DJANGO_ROOT, *args)
    if path.startswith('/home/web/project/'):
        path = path.replace('/home/web/project/', '/home/web/')
    return path


def ensure_secret_key_file():
    """Checks that secret.py exists in settings dir.

    If not, creates one with a random generated SECRET_KEY setting."""
    secret_path = absolute_path('core', 'settings', 'secret.py')
    if not os.path.exists(secret_path):
        from django.utils.crypto import get_random_string
        secret_key = get_random_string(
            50, 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)')
        with open(secret_path, 'w') as f:
            f.write("SECRET_KEY = " + repr(secret_key) + "\n")


def code_release_version():
    """ Read code release version from file."""
    version = absolute_path('version', 'version.txt')
    if os.path.exists(version):
        version = (open(version, 'rb').read()).decode("utf-8")
        if version:
            return version
    return '0.0.1'


def code_commit_release_version():
    """ Read code commit release version from file."""
    version = absolute_path('version', 'commit.txt')
    if os.path.exists(version):
        commit = (open(version, 'rb').read()).decode("utf-8")
        if commit:
            return commit
    return 'no-info'


# Import the secret key
ensure_secret_key_file()
