# coding=utf-8
"""
GeoRepo.

.. note:: Auth for Locust Load Testing
"""

import json
import random
from locust import between, constant


class AuthConfig:
    """Auth users from config json file."""

    DEFAULT_WAIT_TIME = 1  # 1 second

    def __init__(self, file_path='/mnt/locust/locust_auth.json'):
        """Initialize the class."""
        with open(file_path, 'r') as json_file:
            self.users = json.load(json_file)

    def get_user(self):
        """Get random user."""
        user = random.choice(self.users)

        wait_time = constant(self.DEFAULT_WAIT_TIME)
        if user['wait_time_start'] and user['wait_time_end']:
            wait_time = between(
                user['wait_time_start'], user['wait_time_end'])

        return {
            'username': user['username'],
            'api_key': user['api_key'],
            'wait_time': wait_time
        }


auth_config = AuthConfig('locust_auth.json')
